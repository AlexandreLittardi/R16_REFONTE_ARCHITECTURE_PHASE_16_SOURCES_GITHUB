# R16 — Audit complet d’architecture et plan de refonte pas à pas

**Date : 23 octobre 2026. Statut : diagnostic et feuille de route uniquement ; aucun fichier du logiciel de référence n’a été modifié.**

**Base exacte :** `R16_SOURCES_GITHUB_SANS_BUILD.zip` (version GitHub nettoyée). SHA-256 : `8d6c31bc712683cd9a6f1f6c03b6ed6cf47f3f204244612df350234912d02a00`.

**Question posée :** identifier les héritages/masquages, redondances et risques de conception, puis définir un plan de migration sûr et contrôlable. Les recommandations qui suivent constituent un plan, pas une refonte déjà réalisée.

## 1. Résumé décisionnel

**Conclusion : le problème n’est pas principalement la taille du ZIP.** La dette technique vient de l’assemblage par héritage multiple, des états `self.*` partagés entre domaines, des callbacks Tkinter en chaîne et de l’utilisation de méthodes de dessin pour synchroniser des données métier.

| Indicateur | Mesure vérifiée |
|---|---:|
| Fichiers Python de production (dont `mixins/__init__.py`) | 82 |
| Lignes de code Python de production (approximation brute) | 23 087 |
| Mixins directement hérités par `PVLayoutRibbonApp` | 29 |
| Classes de la MRO, application et `object` compris | 38 |
| Définitions de méthodes de classes | 612 |
| Noms de méthodes distincts | 520 |
| Noms ayant plusieurs implémentations sur la MRO | 58 |
| Groupes avec `super()` permettant un parcours jusqu’à l’implémentation terminale (selon AST) | 34 |
| Groupes masqués dès la première implémentation (selon AST) | 22 |
| Groupes dont la chaîne s’interrompt avant le dernier niveau (selon AST) | 2 |
| Implémentations non atteintes par l’appel direct ordinaire du même nom (maximum statique ; non assimilable à du code mort) | 32 |
| Modules Python accessibles depuis `main.py` dans le graphe des imports AST (hors `mixins/__init__`) | 81 / 81 |
| Tests automatisés exécutés | 84 / 84 réussis |
| Couverture globale tests unitaires avec branches, source complète | 13 % |

**Décision proposée :** refonte incrémentale, contractuelle, par sous-systèmes. Conserver les 11 onglets, les fonctionnalités de dessin/électrique/énergie, les JSON anciens, les cotes exactes, les pinces partagées, les exports PDF vectoriels et la sauvegarde entièrement locale. Ne supprimer aucun des 58 groupes uniquement parce qu’un nom est redéfini.

## 2. Méthode, preuves et limites

1. Extraction et analyse AST des **82 fichiers Python** : définition des classes/méthodes, super-appels, appels `self.*`, imports, emplacements `fichier:ligne`.
2. Résolution **réelle à l’import** de `PVLayoutRibbonApp.__mro__` sous Python ; non simple lecture de la liste des mixins.
3. Analyse des dépendances internes : 81 modules locaux atteignables par le graphe des imports depuis `main.py` ; cela **ne prouve pas** que toutes leurs fonctions sont utilisées à l’exécution.
4. `python -m unittest discover -s tests -q` : **84 tests réussis**. Couverture `coverage run --branch --source=.` : **13 %** pour l’ensemble des modules. C’est une photographie des tests unitaires seuls, **pas** la couverture du logiciel sur le terrain.
5. Essais GUI Linux/Xvfb réussis : `test_unified_navigation_gui.py`, `test_mounting_pdf_gui.py`, `test_installation_gui.py`. Ces scripts vérifient le zoom, le pan, la préservation de géométrie et le PDF vectoriel.
6. Ouverture d’une sauvegarde fournie (Frimo) en Tkinter sous Xvfb : **533 panneaux / 9 zones / 2 polygones de câblage / 32 strings** relus et resérialisés. Le premier test était suspendu à une boîte de dialogue modale non automatisée ; il a été corrigé dans le harnais de test, **sans anomalie de chargement démontrée**.
7. **Non testé** dans cet audit : build EXE GitHub/Windows, temps de réponse sur l’ensemble des machines cible, compatibilité de tous les historiques JSON connus, précision physique de chaque calcul d’ingénierie, ni intégration visuelle exhaustive de tous les 11 onglets.

## 3. Diagnostic technique — causes racines (ordre de priorité)

### P0 — A. `draw_grid()` mélange trois responsabilités
**Fichiers :** `mixins/safe_project.py:257`, `mixins/mounting_ui.py:125`, `mixins/editor_interactions.py:82`, `mixins/project_integrity.py:132`, `mixins/canvas_grid.py:701`. **109 méthodes** du code l’appellent directement via `self.draw_grid()` d’après l’AST (les callbacks indirects ne sont pas comptés).

- La couche `SafeProjectMixin.draw_grid` actualise des identifiants de panneaux et planifie une entrée d’historique.
- `ProjectIntegrityMixin.draw_grid` peut synchroniser `diagram_nodes`/`diagram_links` depuis les strings et l’affectation MPPT.
- `MountingMixin.draw_grid` suit une branche différente quand Mounting est actif : il dessine le montage au lieu de poursuivre les mêmes traitements.
- Le rendu d’écran n’est donc pas isolé de l’état projet ; répéter un redraw ou zoom peut déclencher un travail métier sans intention utilisateur.

**Modification :** introduire `ProjectChanged`/`GeometryChanged` comme événements explicites, `SceneRenderer.render(state, camera)` comme fonction de présentation, et une couche de cache/versionnement d’affichage. Faire les mises à jour de numérotation, diagramme, historique uniquement dans les commandes qui changent le modèle. **Ne pas** déplacer ces effets sans test de parité ; ils maintiennent aujourd’hui des invariants implicites.

### P0 — B. Les événements souris traversent trop de mixins
**Fichiers :** `mixins/mounting_ui.py:243/342/363`, `mixins/diagram_editor.py:18/36/49`, `mixins/editor_interactions.py:5/38/61`, `mixins/workspace_improvements.py:378/384/387`, `mixins/canvas_grid.py:23/249/364`. Les séquences gauche `on_left_press/drag/release` comportent chacune **5 implémentations**. Les changements d’onglet `_on_ribbon_tab_changed` en comportent également 5.

**Modification :** une seule fixation des événements Tkinter, un routeur par onglet `ToolController`/`InteractionMode`, puis des commandes explicites (`SelectPanel`, `MoveClamp`, `DragCablePolygon`, etc.). Préserver l’usage actuel : molette zoom ancré curseur, molette enfoncée pour déplacer la vue, gauche pour sélectionner/modifier selon outil. Aucun geste ne doit déclencher deux handlers incompatibles.

### P0 — C. État projet, historique et persistance fortement couplés à l’interface
**Fichiers :** `app.py:78+`, `mixins/project_io.py:25/128`, `mixins/safe_project.py:53/110/141/165`, `project_store.py:15/207/223`, `project_validation.py`. Le constructeur initialise un très grand nombre d’attributs partagés ; `ProjectIOMixin._collect_project_data` nettoie également les strings avant de construire la représentation, et `SafeProjectMixin._record_history` sérialise un document et conserve jusqu’à 100 snapshots.

**Modification :** créer un `ProjectDocument` explicite, un `ProjectRepository` (lecture/écriture atomique, backups, recovery) et un `CommandHistory` (différences métier ou snapshots bornés). Séparer une lecture d’état sans effet secondaire (`snapshot`) des actions de nettoyage/normalisation. Maintenir `schema_version = 2` et les clés existantes à la première étape ; une migration de schéma n’est pas nécessaire pour extraire ces responsabilités.

**Attention :** `SafeProjectMixin._apply_document` appelle volontairement `super()._load_project_file(...)`, bien que `_load_project_file` soit redéfini plus haut ; l’ancienne implémentation n’est donc **pas** à supprimer sur la seule base du masquage.

### P0 — D. Géométrie et disposition des zones liées à des actions UI
**Fichiers :** `mixins/installation_geometry.py:8/136`, `mixins/zone_tools.py:721/824`, `geometry_layout.py`, `zone_registry.py`, `mounting_joint_gap.py`. Les anciennes définitions de `_recalculate_zone_grids` et `generate_panels_from_zones` sont masquées par les nouvelles, mais les nouvelles méthodes assurent des comportements supplémentaires : rotation, entraxes, UID, plages de rangées et préservation d’identifiants.

**Modification :** extraire des fonctions pures `compute_zone_grid`, `place_modules`, `validate_roof_setbacks`, `validate_zone_separation`, `remap_panel_ids`; conserver unités en **mm** pour calculs et une transformation image en **px** clairement isolée. Ne recalculer le calepinage qu’après une action explicite. Une preview montre panneaux conservés/modifiés/supprimés et demande validation si la capacité change.

### P1 — E. Navigation unifiée mais encore surchargée par plusieurs couches
**Fichiers :** `mixins/unified_navigation.py:11/85/94/102`, `view_navigation.py`, anciennes méthodes dans `mixins/diagram_editor.py`, `mixins/responsive_ui.py`, `mixins/canvas_grid.py`. Le `UnifiedNavigationMixin` est prioritaire et masque les anciens zooms ; retirer prématurément ces couches pourrait casser les appels `super` ou les callbacks déjà enregistrés.

**Modification :** `CameraState` indépendante par plan si nécessaire, `CanvasNavigationController` unique, zoom sous curseur, pan molette, limites de zoom, coalescence des événements et rendu de photo recadrée. Ne plus coder les onglets via `idx == 10` dispersé : utiliser des IDs stables (`TabId.MOUNTING`, etc.).

### P1 — F. Contrôleurs électriques, Ombres, Energy/BESS et Spreadsheet peu couverts
**Fichiers :** `mixins/diagram_*.py`, `mixins/shadow_*.py`, `mixins/self_consumption_ui.py`, `mixins/spreadsheet_*.py`, `mixins/safe_project.py:397`, `energy_engine.py`. La méthode `_calculate_self_consumption` de `SafeProjectMixin` remplace les implémentations de 3 couches inférieures, et lance déjà des travaux asynchrones ; une suppression naïve peut retirer calcul, progression, signatures ou protections.

**Modification :** prendre des profils de référence sur les sorties, puis extraire `ElectricalDesignService`, `ShadowService`, `EnergySimulationService` et un moteur de tableur découplé des widgets. Conserver un système d’annulation et des retours sur le thread UI. Contrôler les unités, arrondis, références fabricant et cas de valeurs inconnues.

### P1 — G. Plusieurs générateurs de PDF ont des contrats distincts
**Fichiers :** `mounting_drawing.py`, `mounting_plan_pdf.py`, `mounting_installer.py`, `engineering_report.py`, `report_mounting.py`, `report_plans.py`, `report_studies.py`. Un nom semblable ne signifie pas une redondance : A3 une page, dossier installateur, rapport technique, schéma électrique sont différents.

**Modification :** mutualiser seulement les **primitives vectorielles, styles, cartouches, cotes** dans `rendering/`, avec `MountingPlanExporter`, `InstallerPackageExporter`, `EngineeringReportExporter` distincts. Tests de géométrie/texte du PDF et comparaison visuelle de pages fixes. Aucun LaTeX.

### P2 — H. Nommage, conventions, localisation et distribution
La MRO longue, le mélange de noms français/anglais dans le code, les méthodes gigantesques, les données implicites `self.*` et les `if tab_index` aggravent l’incertitude. Le dépôt n’embarque plus de scripts de build : **ne pas réintroduire** les fichiers PyInstaller/EXE locaux. Préserver une configuration `requirements.txt` et un GitHub Actions configuré ultérieurement par le propriétaire.

## 4. Le vrai sens des 58 redéfinitions

**Important :** le tableau complet figure en annexe CSV. Le décompte suivant est une **analyse statique de la présence de `super()`**, pas une preuve de chemins exécutés : certains `super()` sont conditionnels. Les appels à d’anciennes méthodes depuis un *autre* nom (ex. `_apply_document`) ne sont pas visibles dans un simple tableau de masquage.

| Type | Groupes | Traitement recommandé |
|---|---:|---|
| Chaîne potentielle jusqu’au bas de la MRO | 34 | Conserver temporairement ; extraire chaque responsabilité puis remplacer le flux par une orchestration explicite |
| Premier niveau sans délégation au même nom | 22 | Examiner les appels directs/explicites et les différences ; souvent ancien comportement remplacé, **pas** automatiquement mort |
| Chaîne interrompue dans une couche intermédiaire | 2 | Confirmer si l’implémentation masquée représente volontairement un ancien constructeur d’interface |

**Exemples à suivre en priorité :**

| Méthode | Chaîne ou gagnant réel | Pourquoi la garder sous observation |
|---|---|---|
| `draw_grid` | 5 niveaux | Mutation modèle/historique lors du rendu |
| `on_left_press / on_left_drag / on_left_release` | 5 niveaux chacun | Conflits possibles selon outil et onglet |
| `_on_ribbon_tab_changed` | 5 niveaux | Caches, visibilité, focus et travaux différés |
| `_build_main_area` | 4 niveaux | Bindings et construction dans un ordre fragile |
| `_recalculate_zone_grids` | InstallationGeometryMixin masque ZoneToolsMixin | IDs/row_base/entraxe et remappage |
| `_load_project_file` | SafeProjectMixin masque ProjectIOMixin | La méthode masquée est appelée explicitement par `_apply_document` |
| `_calculate_self_consumption` | SafeProjectMixin prioritaire | Calcul async et ancien calcul synchrone différents |
| `_zoom_at_pointer / _zoom_button_change` | UnifiedNavigationMixin prioritaire | Navigation actuelle doit rester source de vérité |
| `_draw_diagram` | DiagramEditorMixin prioritaire | Rendu et zoom du schéma distincts |
| `_export_engineering_report` | SafeProjectMixin prioritaire | Comparaison du chemin d’export indispensable |

**58 ≠ 58 copies identiques.** L’analyse AST n’a trouvé **aucun corps de méthode strictement identique** parmi les implémentations portant le même nom et résolues dans ces groupes. Elles peuvent se ressembler, mais il faut une preuve de comportement avant suppression.

## 5. Codemap actuelle de référence

```text
main.py
   |
platform_setup.py -> app.PVLayoutRibbonApp (app.py : état + assemblage 29 mixins)
   |
   +-- UI/Tk mixins (11 onglets, toolbar, events, canvas, spreadsheet)
   |      +-- navigation : unified_navigation.py, view_navigation.py
   |      +-- zones/layout : zone_tools.py, installation_geometry.py, canvas_grid.py
   |      +-- montage : mounting_ui/view/edges_ui/chantier.py
   |      +-- électrique : diagram_tools/editor.py, equipment_tools.py
   |      +-- énergie et ombres : self_consumption_ui.py, shadow_*.py
   |
   +-- domaine : geometry_layout.py / mounting*.py / electrical_checks.py
   |             shadow_engine.py / energy_engine.py / self_consumption.py
   |
   +-- état et IO : project_store.py / project_validation.py
   |                 mixins/project_io.py / mixins/safe_project.py
   |
   +-- rendus : mounting_plan_pdf.py / mounting_installer.py
                 engineering_report.py / report_*.py
```

**Nœuds de couplage constatés** (AST : nombres de mixins faisant référence à l’attribut/méthode) : `root` dans 28, `draw_grid` dans 20, `px_per_mm` dans 17, `panels` et `strings` dans 15, `canvas` dans 14. Ce sont des indicateurs de couplage, pas des erreurs de calcul.

**Modules volumineux à scinder après tests :** `mixins/canvas_grid.py` (1 344 lignes), `mixins/spreadsheet_tools.py` (1 286), `mixins/shadow_simulation.py` (1 163), `engineering_report.py` (1 008), `mixins/mounting_ui.py` (864), `mixins/zone_tools.py` (856), `mixins/ui_builders.py` (764).

## 6. Codemap CIBLE — architecture de responsabilité

```text
r16/
  domain/                      # modèles et calculs purs (zéro import tkinter)
    project_document.py         # ProjectDocument, IDs stables, unités explicites
    zones.py                    # géométrie toiture, polygones, marges
    layout.py                   # capacité, placement, rotation, numérotation
    mounting.py                 # pièces physiques, ABC, cotes, BOM
    electrical.py              # strings, MPPT, vérifications
    cabling.py                 # graphe de routes, sections, métrés
    shadow.py                  # ombres et résultats sourcés
    energy.py                  # PV, BESS, consommation, scénarios
    spreadsheet.py             # moteur de cellules et références
  application/                 # cas d’usage et mutations explicites
    project_commands.py        # création/ouverture/édition/autosave
    layout_commands.py         # ChangeZone, RecalculateLayout, MoveModule
    mounting_commands.py       # MoveClamp, SetABC, EditDimensionLabel
    simulation_jobs.py         # exécution/annulation/progrès
    events.py                  # ProjectChanged, LayoutChanged, RenderRequested
    undo_redo.py               # commandes annulables
  infrastructure/
    json_repository.py          # schema v2, validations, migrations, backups
    image_repository.py         # chargement et décalage photo
    pdf_exporters.py            # rapport/montage (exports séparés)
    csv_exporters.py
  rendering/
    camera.py                  # point sous curseur / pan
    canvas_scene.py            # rendu non-mutant + caches
    vector_drawing.py          # cotes et traits réutilisés en PDF
  ui/
    app_shell.py               # 11 onglets, lifecycle
    tab_ids.py                 # IDs stables, pas de nombres magiques
    navigation_controller.py   # un seul binding molette / clic-molette
    event_router.py            # dispatch selon outil + onglet
    tabs/                      # contrôleurs explicites par onglet
      home.py installation.py layout.py stringing.py mppt.py
      shadow.py spreadsheet.py single_line.py cabling.py energy.py mounting.py
  tests/                       # unitaires, intégration JSON, UI, PDF, benchmarks
  main.py                      # bootstrap minimal
```

Il s’agit d’une **cible de responsabilités**, pas d’une obligation de créer tous ces fichiers au premier commit. Éviter une nouvelle classe “manager” contenant tout : chaque sous-module doit posséder des entrées/sorties explicites.

## 7. Plan de changement séquencé, sans régression

### Étape 0 — Figement et reproductibilité
**Objectif :** Référence immuable et contrôles mesurables.

1. Tag/commit de l’archive courante + checksum ; conserver l’ancien lancement Python.
2. Ajouter des fixtures JSON : projet vierge, Frimo 533, ancien schéma, projet sans image, montage 6 ABC, surfaces inclinées.
3. Capturer 11 captures de référence, 3 exports PDF vectoriels, CSV BOM et sauvegarde rechargée ; stocker les métriques comme baseline.

**Critère de sortie :** Aucune donnée ni sortie modifiée. Les 84 tests et les 3 tests GUI constatés sont relançables.

### Étape 1 — Tests d’invariants avant changement
**Objectif :** Sécuriser les zones actuellement non couvertes.

1. Tests schéma/MPPT/câbles/ombre/énergie/tableur, plus cas de valeurs fabricant manquantes.
2. Tests du cycle complet “move routing polygon → save → close → reload”, undo/redo et recovery/backups.
3. Tests “zoom/pan ne modifie pas la sérialisation métier”, “export PDF sans image raster”, “1 pince physique pour 2 contacts compatibles”.

**Critère de sortie :** Chaque invariant métier possède un test automatisé ; audit des pertes de données et différences de résultats.

### Étape 2 — Projet, unités et persistance
**Objectif :** Cesser d’utiliser des widgets Tkinter comme source de vérité.

1. Extraire un `ProjectDocument` lisible et stable sans changer les champs JSON ni `schema_version=2`.
2. Conserver migration des anciens noms (`module_gap_x_mm` etc.) dans un adaptateur dédié ; éviter qu’un redraw retouche le JSON.
3. Distinguer `validate`, `normalize`, `serialize`, `write`; tests round-trip bit à bit sur champs essentiels.

**Critère de sortie :** 533 numéros identiques, 9 zones, 32 strings, 2 polygones ; Undo/Redo et autosave toujours fiables.

### Étape 3 — Commandes métier et historique
**Objectif :** Séparer changement du document et affichage.

1. Créer `execute(command) -> new_state/events`; brancher d’abord une seule action simple comme MovePolygon.
2. Basculer l’historique des mutations vers des commandes ou snapshots métier mesurés ; états de vue séparés.
3. Retirer la collecte de données mutable de `draw_grid` seulement après validation des UID et du diagramme.

**Critère de sortie :** Un appel de rendu pur n’altère pas la signature métier ni l’historique.

### Étape 4 — Rendu et synchronisation
**Objectif :** Réduire le coût et les effets cachés de `draw_grid`.

1. Extraire les 5 couches du pipeline en “update model” puis “build scene” puis “render scene”.
2. Installer des caches invalidés par `LayoutChanged`, `MountingChanged`, `DiagramChanged`, pas par chaque zoom.
3. Conserver en priorité crop photo et taille de texte bornée, vérifier les gros projets.

**Critère de sortie :** Aucun changement de coordonnées physiques pendant zoom/draw. Même dessin/PDF que la baseline.

### Étape 5 — Navigation et distribution des gestes
**Objectif :** Terminer l’unification des vues.

1. Conserver `UnifiedNavigationMixin` comme comportement de référence avant extraction.
2. Introduire `TabId` et `NavigationController` explicite, attaché au canvas une seule fois.
3. Remplacer les chaînes de handlers `on_left_*` par des stratégies par onglet et outil ; créer tests de dispatch.

**Critère de sortie :** Molette zoom, clic-molette pan dans les onglets de dessin ; gauche manipule objets sans mouvement fantôme.

### Étape 6 — Layout et coordonnées réelles
**Objectif :** Géométrie déterministe, numéro stable.

1. Passer `InstallationGeometryMixin`/`ZoneToolsMixin` derrière `LayoutEngine` pur.
2. Ne pas renuméroter silencieusement lors du déplacement/redimensionnement des zones ; validation capacité avant commit.
3. Traiter rotation, pente, entraxes, distances toiture/zones, coordonnées local/global et `row_base` selon un contrat écrit.

**Critère de sortie :** Fixtures géométriques inchangées ; aucune disparition involontaire de panneaux ou string.

### Étape 7 — Mounting et cotation
**Objectif :** Fusionner les modèles, pas les fonctionnalités.

1. Dissocier editor mounting / clamp geometry / physical BOM / dimension labels du canvas.
2. Garantir 6 attaches ABC, pinces partagées (1 physique pour 2 contacts), jeux de pince, masquage et labels sans mutation géométrique.
3. Générer la même scène vectorielle pour canvas et PDF A3, avec validation des quantités et textes.

**Critère de sortie :** Même BOM et coordonnées, PDF vectoriel sans raster, pas de doubles pinces.

### Étape 8 — Electrical, Shadow, Energy, Spreadsheet
**Objectif :** Extraction progressive des plus gros sous-systèmes.

1. Séparer saisie/modèle/calcul/présentation; conserver les signatures de résultats obsolètes à recalculer.
2. Isoler jobs longs et annulation du thread UI ; tests résultats numériques et tableaux sur fixtures.
3. Scinder les grands fichiers seulement lorsque leurs méthodes ont des contrats testés.

**Critère de sortie :** Rapports et métriques numériques inchangés à tolérance physique documentée ; UI réactive.

### Étape 9 — Exports
**Objectif :** Réutiliser les primitives sans mélanger les documents.

1. Exporter A3 montage une page, dossier de pose et rapport ingénierie par adaptateurs distincts.
2. Partage de `Scene`, cotations, cartouche, styles et validateur des cotes en mm.
3. Tests de rendu A3 et de non-rastérisation / sélection des textes.

**Critère de sortie :** Données et nombre d’éléments vectoriels cohérents avec la baseline ; pas de LaTeX.

### Étape 10 — Retrait des mixins et code masqué
**Objectif :** Supprimer uniquement avec preuves d’inutilité.

1. Pour chacun des 58 noms, remplacer une redéfinition par un objet/composant testé.
2. Chercher aussi callbacks `command=`, bindings Tk, `getattr`, références par nom, appels `super` explicites.
3. Supprimer au dernier moment les corps inaccessibles, supprimer les imports devenus inutiles ; conserver une compatibilité JSON.

**Critère de sortie :** La classe App n’a plus de collisions arbitraires ; tests et comparaisons visuelles restent verts.

### Étape 11 — Recette de distribution GitHub
**Objectif :** Verrouiller la stabilité avant release.

1. Tests Python unitaires, GUI sous Linux et Windows, tests performances grands projets, cycles save/export.
2. Contrôles packaging dans GitHub décidés par le propriétaire ; pas de binaires/spec locaux.
3. Mettre à jour README, codemap et tableaux de traçabilité, puis tag de sortie avec plan de rollback.

**Critère de sortie :** Projet JSON et cotes exactes sur toutes plateformes ; version reproductible et documentée.

## 8. Matrice de tests obligatoire / non-régression

| Domaine | Contrôle minimal avant suppression | État actuel |
|---|---|---|
| Startup/11 onglets | Lancement, interaction de chaque onglet, raccourcis | GUI ciblée seulement |
| JSON et autosave | round trip, recovery/backups, anciens fichiers, images absentes | 84 tests + Frimo validé en GUI |
| Installation Area | calibrage, image offset, déplacement polygone, réouverture | GUI installation validée |
| Layout | rotation/zone/panel UID/numéros/strings, 533 panneaux, risque perte | couverture à renforcer |
| Navigation | molette/pan molette, images grandes, rendu constant | GUI navigation validée |
| Mounting | ABC, pinces physiques, BOM, annotation, PDF A3 | forte couverture relative |
| MPPT/Electrical | topologie, tensions et courants et valeurs absentes | couverture faible |
| Shadow | multi-jour, approximation, provenance, invalidations | couverture faible |
| Spreadsheet | formules/références/sauvegarde, Undo | couverture faible |
| Energy/BESS | résultats déterministes, thread/progression/annulation, signatures | couverture faible |
| Cabling | polygones et chemins, longueurs, métrés, sérialisation | tests partiels |
| PDF engineering | mise en page A3, texte, vectoriel, montants/numéros | montage testé, général à renforcer |

**Règle de migration :** un commit = un rôle déplacé, pas plusieurs onglets réécrits simultanément. Chaque phase doit pouvoir être annulée sans conversion irréversible des projets.

## 9. Liste à ne PAS supprimer maintenant

- `mixins/project_io.py:_load_project_file` : appelé explicitement par `SafeProjectMixin._apply_document`, malgré son masquage sur `self`.
- `CanvasGridMixin.draw_grid` : rendu terminal derrière plusieurs extensions (`super()`).
- `mounting_drawing.py`, `mounting_plan_pdf.py`, `mounting_installer.py` : scènes, A3 et dossier installateur ont des contrats différents.
- `project_store.py`, `project_validation.py`, `zone_registry.py` : maintiennent l’ancienne sauvegarde, les UID et les plages de lignes.
- Les alias `gap_x/gap_y` et anciens noms de champs : indispensables pour l’import des historiques.
- Les moteurs des simulations et du tableur : tout projet peut les utiliser même si les tests ne les couvrent pas assez.
- Les implémentations `super` et les callbacks masqués : vérifier leur chemin d’exécution, ne pas déduire leur inutilité d’une recherche textuelle.

## 10. Backlog priorisé et ordre concret des premiers changements

**Premier chantier de code recommandé, après ajout des tests :** `ProjectDocument + ProjectRepository`, avec façade de compatibilité autour de `self` puis commandes d’édition/événements. Cette extraction établit le contrat des données et limite les risques quand `draw_grid` sera rendu pur. En parallèle, conserver l’ancien routeur souris et produire sa matrice de gestes : le remplacer seulement après tests exhaustifs.

| Priorité | Tâche technique | Fichiers actuels ciblés | Preuve de fin |
|---|---|---|---|
| P0 | Fixtures + test planche de référence | `tests/, tools/` | sauvegardes, PDF, screenshots comparables |
| P0 | Document métier immuable / sérialisation déterministe | `app.py, project_io.py, safe_project.py, project_store.py` | round-trip Frimo 533 |
| P0 | Retirer mutations cachées du rendu | `safe_project.py, project_integrity.py, canvas_grid.py` | aucun changement de JSON dû au zoom |
| P0 | Routeur unique des gestes | `mounting_ui.py, diagram_editor.py, editor_interactions.py` | un handler par geste |
| P0 | Lancer recalcul layout uniquement sur commande | `installation_geometry.py, zone_tools.py` | numérotation stable et avertissement capacité |
| P1 | Gestion centrale de caméra / TabId | `unified_navigation.py, view_navigation.py` | conventions globales et zoom stable |
| P1 | Service pinces physiques + PDF | `mounting*.py, mounting_ui.py` | exactitude BOM, cotes et labels |
| P1 | Services électriques et simulation | `diagram_tools.py, self_consumption_ui.py, shadow_*.py` | tests de résultats et progrès |
| P1 | Traitement indépendant des rapports | `engineering_report.py, report_*.py` | PDF propres et non rasterisés |
| P2 | Retirer modules et méthodes véritablement obsolètes | `groupes de la MRO migrés et imports` | aucune régression, codemap cohérente |

## 11. Annexes : les 58 collisions traçables (MRO)

Lecture : `A:nn -> B:mm` indique la résolution Python de la méthode, de la priorité la plus haute à la plus basse. `[s]` : le corps de cette méthode contient un appel syntaxique `super().même_méthode(...)`, parfois conditionnel. Pour chaque groupe, le CSV compagnon inclut aussi le nombre d’appels statiques et les fichiers référents.

| Méthode | Catégorie | Résolution (classe@ligne ; `[s]` si `super`) |
|---|---|---|
| `_build_main_area` | chaîne potentielle | UnifiedNavigationMixin:11[s] → MountingMixin:85[s] → DiagramEditorMixin:14[s] → ZoneToolsMixin:21 |
| `_build_material_spreadsheet_area` | chaîne potentielle | SpreadsheetInteractionsMixin:34[s] → SpreadsheetToolsMixin:412 |
| `_build_root_scroller` | masquage immédiat | ResponsiveUIMixin:13 → UIBuildersMixin:157 |
| `_build_self_consumption_tab` | chaîne potentielle | SafeProjectMixin:388[s] → SelfConsumptionMixin:16 |
| `_build_tab_diagram_tools` | chaîne potentielle | DiagramEditorMixin:8[s] → DiagramToolsMixin:42 |
| `_build_tab_file_tools` | chaîne interrompue | SafeProjectMixin:31[s] → ProjectWorkspaceMixin:8[s] → WorkspaceImprovementsMixin:18 → UIBuildersMixin:342 |
| `_build_tab_layout_tools` | chaîne interrompue | SafeProjectMixin:461[s] → WorkspaceImprovementsMixin:31 → UIBuildersMixin:476 |
| `_calculate_self_consumption` | masquage immédiat | SafeProjectMixin:397 → ProjectWorkspaceMixin:78[s] → WorkspaceImprovementsMixin:306[s] → SelfConsumptionMixin:204 |
| `_delete_selected_diagram_node` | masquage immédiat | EditorInteractionsMixin:76 → DiagramToolsMixin:405 |
| `_diagram_node_size` | masquage immédiat | DiagramEditorMixin:99 → DiagramToolsMixin:521 |
| `_diagram_screen_node_size` | masquage immédiat | DiagramEditorMixin:134 → DiagramToolsMixin:418 |
| `_download_historical_weather` | masquage immédiat | SafeProjectMixin:419 → SelfConsumptionMixin:168 |
| `_draw_cable_network_routes` | chaîne potentielle | TwoPoleCablesMixin:93[s] → CableNetworkMixin:493 |
| `_draw_diagram` | masquage immédiat | DiagramEditorMixin:141 → DiagramToolsMixin:559 |
| `_draw_spreadsheet_selection` | chaîne potentielle | SpreadsheetInteractionsMixin:49[s] → SpreadsheetToolsMixin:755 |
| `_export_cable_routes_csv` | chaîne potentielle | WorkspaceImprovementsMixin:448[s] → NotesToolsMixin:348 |
| `_export_engineering_report` | masquage immédiat | SafeProjectMixin:517 → ProjectWorkspaceMixin:69 |
| `_export_self_consumption` | chaîne potentielle | WorkspaceImprovementsMixin:450[s] → SelfConsumptionMixin:341 |
| `_export_spreadsheet_csv` | chaîne potentielle | WorkspaceImprovementsMixin:449[s] → SpreadsheetToolsMixin:1147 |
| `_get_active_tab_index` | chaîne potentielle | SafeProjectMixin:282[s] → CanvasGridMixin:1339 |
| `_get_cell_coords` | chaîne potentielle | InstallationGeometryMixin:123[s] → CanvasGridMixin:1300 |
| `_get_panel_physical_center` | chaîne potentielle | InstallationGeometryMixin:118[s] → StringingToolsMixin:225 |
| `_import_historical_weather` | masquage immédiat | SafeProjectMixin:465 → SelfConsumptionMixin:157 |
| `_init_spreadsheet_state` | chaîne potentielle | SpreadsheetInteractionsMixin:27[s] → SpreadsheetToolsMixin:204 |
| `_install_energy_workspace` | masquage immédiat | ProjectWorkspaceMixin:33 → WorkspaceImprovementsMixin:258 |
| `_install_home` | chaîne potentielle | ProjectWorkspaceMixin:85[s] → WorkspaceImprovementsMixin:108 |
| `_install_responsive_ui` | chaîne potentielle | SafeProjectMixin:234[s] → ResponsiveUIMixin:18 |
| `_load_project_file` | masquage immédiat | SafeProjectMixin:141 → ProjectIOMixin:128 |
| `_on_canvas_motion` | chaîne potentielle | MountingMixin:367[s] → PathsToolsMixin:332 |
| `_on_diagram_list_select` | masquage immédiat | EditorInteractionsMixin:72 → DiagramToolsMixin:525 |
| `_on_escape_key` | chaîne potentielle | MountingMixin:388[s] → PathsToolsMixin:385 |
| `_on_ribbon_tab_changed` | chaîne potentielle | MountingMixin:105[s] → DiagramEditorMixin:290[s] → WorkspaceImprovementsMixin:311[s] → ResponsiveUIMixin:8[s] → ZoneToolsMixin:285 |
| `_on_spreadsheet_cell_click` | chaîne potentielle | SpreadsheetInteractionsMixin:74[s] → SpreadsheetToolsMixin:834 |
| `_on_zone_combo_selected` | chaîne potentielle | EditorInteractionsMixin:90[s] → ZoneToolsMixin:625 |
| `_read_shadow_params_from_entries` | chaîne potentielle | ProjectIntegrityMixin:67[s] → ShadowToolsMixin:379 |
| `_rebuild_spreadsheet_grid` | chaîne potentielle | SpreadsheetInteractionsMixin:20[s] → SpreadsheetToolsMixin:659 |
| `_recalculate_zone_grids` | masquage immédiat | InstallationGeometryMixin:8 → ZoneToolsMixin:721 |
| `_recompute_shadow` | chaîne potentielle | SafeProjectMixin:277[s] → ShadowToolsMixin:469 |
| `_refresh_energy_workspace` | chaîne potentielle | ProjectWorkspaceMixin:49[s] → WorkspaceImprovementsMixin:283 |
| `_remember_recent_project` | chaîne potentielle | SafeProjectMixin:162[s] → WorkspaceImprovementsMixin:343 |
| `_reset_zoom` | masquage immédiat | UnifiedNavigationMixin:102 → DiagramEditorMixin:263[s] → UIBuildersMixin:276 |
| `_show_help` | masquage immédiat | WorkspaceImprovementsMixin:328 → UIBuildersMixin:215 |
| `_zone_rotate_rect` | masquage immédiat | InstallationGeometryMixin:101 → ZoneToolsMixin:811 |
| `_zoom_at_pointer` | masquage immédiat | UnifiedNavigationMixin:85 → MountingMixin:412[s] → DiagramEditorMixin:249[s] → ResponsiveUIMixin:138[s] → CanvasGridMixin:561 |
| `_zoom_button_change` | masquage immédiat | UnifiedNavigationMixin:94 → DiagramEditorMixin:257[s] → ResponsiveUIMixin:134[s] → UIBuildersMixin:268 |
| `compute_all_cable_routes` | masquage immédiat | TwoPoleCablesMixin:69 → CableNetworkMixin:465 |
| `compute_cable_length_mm` | masquage immédiat | TwoPoleCablesMixin:65 → CableNetworkMixin:457 |
| `delete_active_zone` | masquage immédiat | InstallationGeometryMixin:81 → ZoneToolsMixin:633 |
| `draw_grid` | chaîne potentielle | SafeProjectMixin:257[s] → MountingMixin:125[s] → EditorInteractionsMixin:82[s] → ProjectIntegrityMixin:132[s] → CanvasGridMixin:701 |
| `export_csv` | chaîne potentielle | WorkspaceImprovementsMixin:446[s] → ProjectIOMixin:402 |
| `export_mppt_csv` | chaîne potentielle | WorkspaceImprovementsMixin:447[s] → EquipmentToolsMixin:96 |
| `generate_diagram_auto` | chaîne potentielle | DiagramEditorMixin:231[s] → DiagramToolsMixin:134 |
| `generate_panels_from_zones` | masquage immédiat | InstallationGeometryMixin:136 → ZoneToolsMixin:824 |
| `on_left_drag` | chaîne potentielle | MountingMixin:342[s] → DiagramEditorMixin:36[s] → EditorInteractionsMixin:38[s] → WorkspaceImprovementsMixin:384[s] → CanvasGridMixin:249 |
| `on_left_press` | chaîne potentielle | MountingMixin:243[s] → DiagramEditorMixin:18[s] → EditorInteractionsMixin:5[s] → WorkspaceImprovementsMixin:378[s] → CanvasGridMixin:23 |
| `on_left_release` | chaîne potentielle | MountingMixin:363[s] → DiagramEditorMixin:49[s] → EditorInteractionsMixin:61[s] → WorkspaceImprovementsMixin:387[s] → CanvasGridMixin:364 |
| `on_right_drag` | chaîne potentielle | MountingMixin:408[s] → DiagramEditorMixin:66[s] → CanvasGridMixin:506 |
| `on_right_press` | chaîne potentielle | MountingMixin:402[s] → DiagramEditorMixin:55[s] → CanvasGridMixin:469 |

## 12. Verdict

La refonte est justifiée pour **fiabiliser** les évolutions (notamment Layout, navigation, sauvegarde, Mounting), et secondairement pour réduire le code et le coût de maintenance. **La suppression immédiate de 58 méthodes serait dangereuse.** Le chemin sûr est : **protéger les invariants → isoler les données → contrôler les mutations → découpler les rendus et événements → extraire domaine/UI → supprimer les couches devenues réellement inutiles.**

**État du livrable : audit seulement.** Aucun changement apporté à la version R16 contenue dans l’archive de référence.
