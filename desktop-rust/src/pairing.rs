use crate::{
    library::Library,
    sources::{self, R, SOURCES},
};
use base64::{engine::general_purpose::URL_SAFE_NO_PAD as B64, Engine};
use ring::{
    aead,
    rand::{SecureRandom, SystemRandom},
};
use serde_json::{json, Value};
use std::{
    io::{Read, Write},
    net::{Ipv4Addr, SocketAddr, TcpListener, UdpSocket},
    time::{Duration, Instant},
};
const PREFIX: &str = "artfinder-pair:v1:";
const AAD: &[u8] = b"ArtFinder pairing v1";
fn random<const N: usize>() -> R<[u8; N]> {
    let mut b = [0; N];
    SystemRandom::new()
        .fill(&mut b)
        .map_err(|_| "Falha no gerador de chaves")?;
    Ok(b)
}
fn cipher(k: &[u8]) -> R<aead::LessSafeKey> {
    Ok(aead::LessSafeKey::new(
        aead::UnboundKey::new(&aead::AES_256_GCM, k).map_err(|_| "Chave inválida")?,
    ))
}
pub fn categories(db: &Library) -> R<Value> {
    let mut result = json!({});
    for (name, tags) in db.names("category")? {
        let meta = db
            .names("category_meta")?
            .into_iter()
            .find(|(k, _)| k == &name)
            .and_then(|(_, v)| serde_json::from_str::<Value>(&v).ok())
            .filter(Value::is_object);
        result[&name] = meta.unwrap_or_else(|| json!({"label":name}));
        result[&name]["tags"] = json!(tags);
        result[&name]["favorite"] = json!(db
            .names("favorite_category")?
            .iter()
            .any(|(k, _)| k == &name));
        result[&name]["source_tags"] = json!({});
        for s in SOURCES {
            if let Some((_, q)) = db
                .names(&format!("tags/{s}"))?
                .into_iter()
                .find(|(n, _)| n == &name)
            {
                result[&name]["source_tags"][s.to_lowercase()] =
                    json!(q.split(';').map(str::trim).collect::<Vec<_>>());
            }
        }
    }
    Ok(result)
}
pub fn export(db: &Library, keys: bool) -> R<String> {
    let mut credentials = json!({});
    if keys {
        for k in sources::KEYS {
            if let Some(v) = sources::credential(k) {
                credentials[k] = json!(v)
            }
        }
    }
    let payload = json!({"version":1,"source":"ArtFinder Rust","sections":{"categories":true,"credentials":keys},"categories":categories(db)?,"credentials":credentials});
    let mut bytes = serde_json::to_vec(&payload).map_err(|_| "Configuração inválida")?;
    if bytes.len() > 512 * 1024 {
        return Err("Configuração muito grande".into());
    }
    let key = random::<32>()?;
    let nonce = random::<12>()?;
    cipher(&key)?
        .seal_in_place_append_tag(
            aead::Nonce::assume_unique_for_key(nonce),
            aead::Aad::from(AAD),
            &mut bytes,
        )
        .map_err(|_| "Falha ao criptografar")?;
    let envelope=json!({"version":1,"algorithm":"AES-256-GCM","nonce":B64.encode(nonce),"ciphertext":B64.encode(bytes),"expires_at":chrono::Utc::now().timestamp()+300}).to_string();
    let udp = UdpSocket::bind("0.0.0.0:0").map_err(|_| "Rede indisponível")?;
    udp.connect("192.0.2.1:9")
        .map_err(|_| "Rede indisponível")?;
    let SocketAddr::V4(ip) = udp.local_addr().map_err(|_| "Rede indisponível")? else {
        return Err("Sem IPv4 local".into());
    };
    if !ip.ip().is_private() {
        return Err("Conecte os dispositivos à mesma rede privada".into());
    }
    let listener = TcpListener::bind((*ip.ip(), 0)).map_err(|_| "Falha ao abrir conexão local")?;
    listener
        .set_nonblocking(true)
        .map_err(|_| "Rede indisponível")?;
    let addr = listener.local_addr().map_err(|_| "Rede indisponível")?;
    let path = format!("/v1/pair/{}", B64.encode(random::<32>()?));
    let code = format!(
        "{PREFIX}{}",
        B64.encode(json!({"key":B64.encode(key),"url":format!("http://{addr}{path}")}).to_string())
    );
    std::thread::spawn(move || {
        let end = Instant::now() + Duration::from_secs(300);
        while Instant::now() < end {
            if let Ok((mut stream, _)) = listener.accept() {
                let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
                let _ = stream.set_write_timeout(Some(Duration::from_secs(2)));
                let mut buf = [0; 4096];
                let n = stream.read(&mut buf).unwrap_or(0);
                let line = String::from_utf8_lossy(&buf[..n]);
                let serve = line.lines().next() == Some(&format!("GET {path} HTTP/1.1"))
                    && Instant::now() < end;
                let (status, body) = if serve {
                    ("200 OK", envelope.as_str())
                } else {
                    ("404 Not Found", "")
                };
                let _=write!(stream,"HTTP/1.1 {status}\r\nContent-Type: application/json\r\nCache-Control: no-store\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",body.len());
                if serve {
                    break;
                }
            } else {
                std::thread::sleep(Duration::from_millis(100))
            }
        }
    });
    Ok(code)
}
pub fn fetch(code: &str) -> R<Value> {
    let bad = "Código de pareamento inválido";
    if code.len() > 12000 {
        return Err(bad.into());
    }
    let desc: Value = serde_json::from_slice(
        &B64.decode(code.trim().strip_prefix(PREFIX).ok_or(bad)?)
            .map_err(|_| bad)?,
    )
    .map_err(|_| bad)?;
    let endpoint = url::Url::parse(desc["url"].as_str().ok_or(bad)?).map_err(|_| bad)?;
    if endpoint.scheme() != "http"
        || !endpoint
            .host_str()
            .and_then(|h| h.parse::<Ipv4Addr>().ok())
            .is_some_and(|ip| ip.is_private())
        || endpoint.port().is_none()
        || !endpoint.username().is_empty()
        || endpoint.password().is_some()
        || endpoint.query().is_some()
        || endpoint.fragment().is_some()
        || !endpoint.path().starts_with("/v1/pair/")
    {
        return Err(bad.into());
    }
    let key = B64
        .decode(desc["key"].as_str().ok_or(bad)?)
        .map_err(|_| bad)?;
    let cipher = cipher(&key)?;
    let agent = ureq::AgentBuilder::new()
        .redirects(0)
        .timeout(Duration::from_secs(5))
        .build();
    let resp = agent
        .get(endpoint.as_str())
        .call()
        .map_err(|_| "Pareamento expirado ou inacessível")?;
    if resp.status() != 200 {
        return Err(bad.into());
    }
    let doc: Value = serde_json::from_reader(resp.into_reader().take(750000)).map_err(|_| bad)?;
    if doc["algorithm"] != "AES-256-GCM" || doc["version"] != 1 {
        return Err(bad.into());
    }
    let nonce = B64
        .decode(doc["nonce"].as_str().ok_or(bad)?)
        .map_err(|_| bad)?;
    let mut data = B64
        .decode(doc["ciphertext"].as_str().ok_or(bad)?)
        .map_err(|_| bad)?;
    let plain = cipher
        .open_in_place(
            aead::Nonce::try_assume_unique_for_key(&nonce).map_err(|_| bad)?,
            aead::Aad::from(AAD),
            &mut data,
        )
        .map_err(|_| bad)?;
    if plain.len() > 512 * 1024 {
        return Err(bad.into());
    }
    let payload: Value = serde_json::from_slice(plain).map_err(|_| bad)?;
    if payload["version"] != 1 {
        return Err(bad.into());
    }
    Ok(payload)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn invalid_codes_fail_before_transfer() {
        assert!(fetch("bad").is_err());
        for url in [
            "http://127.0.0.1:5000/v1/pair/x",
            "https://example.com:5000/v1/pair/x",
        ] {
            let code = format!(
                "{PREFIX}{}",
                B64.encode(json!({"url":url,"key":"test"}).to_string())
            );
            assert!(fetch(&code).is_err())
        }
    }
    #[test]
    #[ignore = "requer interface de rede local"]
    fn lan_roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let db = Library::open(dir.path()).unwrap();
        db.set("category", "Teste", "landscape").unwrap();
        let code = export(&db, false).unwrap();
        let payload = fetch(&code).unwrap();
        assert_eq!(payload["categories"]["Teste"]["tags"], "landscape");
        assert_eq!(payload["credentials"], json!({}));
        assert!(fetch(&code).is_err());
    }
}
