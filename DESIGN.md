# ArtFinder desktop

A native image library for finding, comparing and saving artwork. The desktop
surface operates as a tool: familiar navigation, compact controls, visible
selection and artwork as the main content. The Qt client is the PC target;
the separate browser and Android clients retain their own layouts.

## Visual system

- Charcoal canvas #202124, surface #292b2f, text #f1f2f4, secondary text #b1b5bd,
  divider #454951 and selection/action blue #84b7ff.
- Source Sans 3 for controls and metadata, Archivo for the product mark and titles.
- 200 px sidebar, compact workspace toolbar, flexible grid and 230–330 px inspector.
  The inspector can be hidden; the grid adapts to thumbnail size and window width.
- Native desktop density: 13 px control text, 20 px titles, explicit button edges,
  5–6 px control corners and visible keyboard focus. Minimum window: 1000 × 680.
- Persistent Night, Graphite, Forest and Light themes. Dark is the default.
- No decorative hero, generated illustrations, purple wash or marketing cards.
  Identity comes from the compass mark, consistent icons and the library composition.

## Interaction

Search by tags from the empty state; choose categories/sources in New search.
Select to inspect, double-click to open, Ctrl-click for batch actions. Collection
names and artwork metadata are user content. Never translate or reinterpret them.
Protected media must not be requested by either grid or inspector before reveal.
Loading, empty, unavailable-image and disabled states must explain what is happening.

## References and validation

[Eagle](https://eagle.cool/support/get-started) informs the library/inspector
structure. [PureRef](https://www.pureref.com/handbook/canvas/) informs the focus on
artwork. Neither product's assets are bundled. No AI-generated imagery is used.
Validate native captures at 1440 × 900 and 1000 × 680, all themes, selection,
protected media, dialogs and keyboard interaction. Screenshots use synthetic test
fixtures; actual artwork comes from the user's configured sources.
