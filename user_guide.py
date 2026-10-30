"""Practical English help for the controls and calculations in this release.

WORKFLOWS is consumed by the Home guide. Tab titles are kept exact so their
live toolbar command catalogue remains attached to the corresponding help.
"""

WORKFLOWS = [
('Home', '''WHAT THIS APPLICATION DOES
Build a scaled PV layout, organise modules into inverter blocks and ordered strings, assign MPPTs, estimate DC routes, study shading and compare PV-only / one-BESS / two-BESS energy balances. Calculations depend on the entered geometry, equipment and source data. A populated drawing is not the same as a complete engineering model.

WHERE TO FIND HELP
Home > Guide > How it works contains this manual. Select a topic in the left list and scroll its text. For a workspace topic, the live Toolbar commands catalogue appears below the instructions. Home > Guide > Formulas explains the calculation equations. Read First launch if this is your first project, Getting started for a complete workflow, Engineering inputs for the questionnaire and Troubleshooting when a calculation stops.

OPEN OR START
Existing project: Project > Open JSON project, then verify the roof image, scale, actual module count and equipment. Recent projects are shortcuts to files; an entry can stop working if the file is moved.
New project: Project > Load roof image, calibrate a known distance in Installation area, then Save as a new JSON. Loading an image alone does not calibrate it. Choose a meaningful filename: the PDF title uses the saved filename with underscores replaced by spaces and the .json extension removed.

CONFIGURATION
Home > Configuration opens the engineering questionnaire. Fields marked * are required by the questionnaire. Use the section selector to jump to a group. Required fields only is a filter, not a declaration that all calculations are ready. Uncheck it to review optional manufacturer limits and model assumptions. Per-string operating overrides are edited in Cabling > Edit selected string. Apply all inputs validates and commits the draft. Cancel closes it without applying the draft.

WORK IN DEPENDENCY ORDER
Scale and zones -> layout -> inverter blocks and equipment -> strings -> MPPTs -> inverter locations and cable paths -> routes and sizing -> shading -> consumption and weather -> Energy / BESS -> spreadsheet and exports. Changing an earlier input can invalidate later results. Save at each major milestone and recalculate affected results before exporting.

LONG TASKS
Watch the progress display. Use Cancel or Cancel calculation for a running task and wait for it to finish cancelling before starting another. Undo/Redo and some configuration operations are unavailable during calculations. Never interpret an old chart as a new result merely because it is still stored in the project.'''),

('First launch', '''WHAT YOU ARE OPENING
This application creates a photovoltaic project: a roof plan, numbered modules, their electrical strings, inverter connections and engineering calculations. A project JSON stores the editable inputs. PDF, JPG, SVG and CSV files are exports for reading or sharing; opening an export does not load an editable project.

FIND YOUR WAY AROUND
The tabs across the top choose a workspace. Home contains this guide, project commands and Configuration. Installation area is where you calibrate the roof image and draw usable areas. Layout and blocks places modules and groups them by inverter. Stringing defines series connections. MPPT assignment connects those strings to inverter inputs. Shadow studies shading. Spreadsheet calculates project quantities. Electrical single-line diagram draws connections. Cabling prepares conductor routes and sizing. Energy / BESS compares production, load and storage.
Click the text of a tab to switch workspace. The command bar contains buttons and menus. A button performs an action or opens a dialog; a menu reveals commands when clicked. Commands in this guide are identified by their written labels. The side lists identify project objects, while the central drawing is the canvas. Select the intended item in its list before editing or deleting it.

START WITH AN EXISTING PROJECT
1. In Home, open Project and choose Open JSON project. Browse to the project .json file and open it.
2. If prompted about current changes, choose Yes to save them, No to leave them behind, or Cancel to keep the current project open.
3. Check the active project name, roof image and module count. If the roof image is missing, use Project > Load roof image and choose the matching original image. Keep its geometry consistent with the saved layout.
4. Use Save as to create your working copy. Choose a folder and a meaningful filename; future Save commands use that filename.
5. Open Configuration and review equipment, site, time zone, elevations and calculation assumptions. A loaded project can contain incomplete inputs or results that need recalculation.

START WITHOUT A PROJECT
1. In Home, choose Project > Load roof image. Use a plan with a known real-world distance. Choose Save as to name the new project.
2. Switch to Installation area. Calibration converts image pixels to real distances: draw the reference segment, enter its real length in millimetres and apply the scale. For a 10 metre segment, enter 10000 mm. Check another known distance before placing modules.
3. Draw a rectangular installation zone by dragging from one corner to the opposite corner. This is the physical area where modules may be placed, not an inverter or an electrical string.
4. Open Home > Configuration. Under Additional records, choose Add module and enter the actual module datasheet values. Add inverter records for the equipment you intend to use. Click Apply all inputs to apply the draft.
5. Open Layout and blocks, review Panel settings and generate the layout. Check the module count and that modules remain inside the usable roof areas.
6. Continue with Getting started to create inverter blocks, strings and MPPT assignments before calculating energy or cables.

MOUSE AND SELECTION
Left-click means press and release the left mouse button. Drag means keep the button held while moving, then release. Ctrl-click and Shift-click mean hold that keyboard key while clicking. Right-click uses the right mouse button. Selection identifies the object a command will edit; selecting an object does not by itself create a connection. Drawing modes can give clicks another purpose, so finish or cancel the active mode before selecting another object. The workspace topics explain their specific mouse actions.

READ A FIELD BEFORE ENTERING A VALUE
mm means millimetres; m means metres. W and kW are power; kWh is energy accumulated over time. A module tilt such as 8 degrees is its inclination above horizontal. A layout rotation is a rotation of placement on the image. These are separate inputs. A cable installation elevation is also separate from the roof receiver height used for shadows.

APPLY, SAVE AND CALCULATE
Apply changes the project inputs; Save writes them to disk; Calculate produces results from those inputs. Perform all three when appropriate. A chart retained in the project may become outdated after an edit. Recalculate affected studies before using a result or exporting it. Undo restores a recorded project state and Redo reapplies an undone change; save a checkpoint before major editing.

IF A STEP STOPS
Read the complete error or status message. Check the prerequisites in the relevant guide topic rather than filling a missing value with an arbitrary number. Save your working copy, note the action and exact message, and keep the JSON available if you need support.'''),

('Getting started', '''FIRST COMPLETE PROJECT: A CHECKED WORKFLOW
1. Open the project or load a roof image. Save under a new name before experimenting with an existing installation. Keep the JSON and its saved roof image together.
2. In Installation area, draw a scale reference over a known distance and enter its real length in mm. Check a second distance. Stop if the image scale is inconsistent.
3. Draw one rectangular zone per physical installation area. Reserve access routes and exclusions; configure module gaps and edge clearances where needed. Enter separate roof heights for shading and installation elevations for cable routing.
4. In Configuration, enter the actual module dimensions, Pmax, Voc, Isc, Vmp, Imp, thermal assumptions and design temperatures. Set the site's coordinates, time zone and north reference. Check each default.
5. In Layout and blocks, Generate layout. Inspect the zone boundaries, empty spaces, module count and overlap warnings. A module must fit completely within its zone.
6. Create one inverter block per inverter, add the inverter equipment and assign existing modules to the correct block. Place each inverter. An inverter block is an electrical grouping, not a physical roof zone.
7. Create or automatically generate strings. Inspect every string's ordered module list. Confirm the intended inverter block and compatible orientation before assigning an MPPT.
8. In MPPT assignment, review string-input capacity and manufacturer voltage/current checks. Supply missing ratings instead of treating incomplete checks as passed.
9. In Cabling, define trays, routing areas, gathering points, elevations, terminal heights and reserves. Calculate routes, then inspect each A/B length, route method, section, voltage drop and check status.
10. In Shadow, check a known sun position and run the intended period. Set the annual shadow-study year for the report.
11. Import consumption, then weather if available. Enter BESS settings and the grid export limit. Calculate the three options. Check the period, source, energy balances and final SOC.
12. Review the spreadsheet, save the JSON and export the required drawings, schedules and report. Open the generated files and inspect them.

MINIMUM SUCCESS CHECKS
The number of modules agrees across the layout and zone variables. Every intended string has the right modules and an MPPT. Every intended inverter has real equipment and a position. Routes are current or explicitly unavailable. Energy results are current or explicitly unavailable. Missing values are visible, not silently replaced.

IF YOU ONLY NEED A LAYOUT
Complete steps 1-5 and save/export the geometry. You do not need to invent BESS, consumption or cable data to produce a plan. A report can include available results and explain unavailable calculations.'''),

('Engineering inputs', '''USE THE QUESTIONNAIRE AS YOUR INPUT REGISTER
Open Home > Configuration. Choose a section in the drop-down list; scroll within the window. Required fields only hides other fields temporarily. Draft values are retained when rebuilding the questionnaire. Apply all inputs commits validated changes as one project edit; a validation error leaves the dialog open so you can correct it.

SOURCE FILES
Choose the roof image, consumption .xlsx/.csv and weather JSON here if desired. Leave a path blank to retain its loaded source. Blank paths do not mean delete the source. Consumption must be loaded before weather. Replacing consumption clears its previous weather association, so import suitable weather again.

GEOMETRY AND SITE
Module width/height, gaps and clearances: mm. Tilt: angle above horizontal in degrees. Azimuth: compass direction in degrees, measured from north; south is 180 degrees. Layout rotation: rotation of the placement grid in the image plane, not module tilt. Coordinates: latitude/longitude in degrees. Select the site's actual time zone. North correction aligns the image with the geographical reference.
Cable installation elevation: m above a common routing datum. Roof/obstacle heights used for shading: mm. These are different inputs, even if they describe the same physical roof.

EQUIPMENT
Module values: Pmax in W; Voc/Vmp in V; Isc/Imp in A. Enter coefficients and temperature limits in the units shown next to their fields. Inverter active power is kW. Apparent power is kVA: the energy model needs active power, or apparent power together with a declared power factor. Do not assume kVA equals kW. Enter MPPT input counts, string-input capacity, voltage window and current limits from the actual model.

STRING CABLE INPUTS
Current is the string operating current in A. Voltage is the total operating voltage of the series string in V, not a single-module Vmp. Section is mm2; corrected ampacity and protection rating are A; manufacturer linear mass is kg/m. Overrides are string-specific. Additional cable inventory declares cables outside the automatic A+B string routes.

ENERGY, STORAGE AND ECONOMICS
Consumption values are kWh over each interval. Cabinet capacity is kWh; charging/discharging limits and export limits are kW. SOC and efficiency are percentages. Enter tariffs in EUR/kWh, investment/annual costs in EUR and discount/degradation values in the indicated units. Do not enter 0.95 into a field requesting 95 percent.

ADDING OR REMOVING RECORDS
Additional records creates the available equipment or cable records on the same questionnaire. New engineering inputs are editable immediately. Remove deletes the selected supported record from the draft; apply to commit it. Recheck any inverter or string that depended on a removed equipment row.

WHAT A STAR DOES NOT GUARANTEE
A valid questionnaire can still have missing source data, incomplete routes or disconnected modules. After applying it, check the actual layout, assignments, routing statuses and calculation readiness. Empty optional manufacturer data remains missing; 0 is a declared value, not a substitute for unknown data.'''),

('Save and Undo', '''SAVE A WORKING PROJECT
Project > Save project updates the current JSON. Save as creates a separate project filename: use it for alternatives and important milestones. The JSON is the editable project, including equipment, strings, spreadsheet and stored inputs. A JPG, CSV or PDF is an export, not a replacement for it.

PORTABLE FILES
Keep the JSON with its saved roof image. Copy the complete project set when moving to another computer, then open the copied JSON and verify the image and scale before continuing. A recent-project shortcut points to the old location; use Open JSON project if the project was moved.

RECOVERY AND BACKUPS
Normal saves use atomic replacement and retain backup versions. Automatic recovery writes a separate recovery copy rather than deliberately overwriting the reference project. Recovery files live under .recovery and backups under .backups in the relevant project/save location. If the main file is damaged, first preserve it, then open a suitable recovery or backup JSON and Save as a new filename. Verify the corresponding image and project date. A recovery copy is not proof that your latest edits were saved to the main file.

UNDO AND REDO
Undo/Redo are available in every workspace and share one project history. Ctrl+Z undoes; Ctrl+Y or Ctrl+Shift+Z redoes. Check the plan and dependent tables after either operation: a change can affect more than the tab currently visible. Drawing and typing edits are grouped with a short delay; history retains up to 100 states.
A new edit after Undo clears the redo branch. Opening another project starts a new history. Undo cannot recover a previous session; use saved versions instead. Undo/Redo are disabled while a background calculation is running.

WHEN CHANGING PROJECTS OR CLOSING
Respond to the unsaved-changes prompt. Save keeps the changes; discarding loses those edits from the working project. Cancel keeps the current project open. If you need a named alternative, use Save as before opening another file.

GOOD CHECKPOINTS
Save after verified calibration, after a checked layout, after string/MPPT assignment, after routing and after final calculations. Before major geometry changes, Save as a variant rather than relying entirely on Undo.'''),

('Installation area', '''GOAL AND PREREQUISITES
Define correctly scaled physical areas and routing surfaces before generating panels or calculating cable lengths. Start with a plan whose real dimensions are known. The app measures its image geometry; perspective-distorted photos can produce inconsistent dimensions.

1. CALIBRATE THE IMAGE
Scale and measurements > Draw scale reference: draw between the endpoints of a known distance. Enter the true distance in millimetres. Example: 10 m is 10000 mm. Measure a second known feature to check the result. A wrong scale changes dimensions, module fit, cable lengths and shadow geometry simultaneously.

2. DRAW AND CHECK RECTANGULAR ZONES
Zones > Draw rectangular zone: drag opposite corners. Select the zone in the list. Transform zones lets you move it or resize its handles. Settings edits the available exact geometry/alignment parameters. Review the boundary against the actual roof and the intended installation area. Zones are physical areas; they need not match inverter blocks.
Do not reserve a fire/access corridor merely by drawing a decorative measurement. Use the installation boundaries, configured edge clearance or exclusions to leave it free of panels.

3. DEFINE CABLE ROUTING AREAS
Cable routing area > Draw cable routing area: left-click successive vertices; right-click finishes; Escape cancels. Use Transform selected area to move its interior or adjust vertices. This mode transforms the polygon and does not select modules underneath. Review the finished polygon for crossings or degenerate edges.

4. ENTER ELEVATIONS
Zones > Installation heights, or the corresponding cable-routing-area command, opens the routing elevation controls. Use metres relative to one consistent datum. Give every relevant zone and routing polygon an elevation, plus the inverter terminal height. Set the bridge threshold only when an unsupported gap really has a supported crossing. Conflicting or missing surface elevations can block a route.
Shadow roof height is a separate field in millimetres. Supplying it does not complete a missing cable height.

5. ADD DIMENSIONS
Choose aligned, horizontal or vertical dimension and drag its endpoints. Horizontal/vertical dimensions show projections, not diagonal length. Drag a dimension's label to position its dimension line; Ctrl-right-click the label deletes it. Values are mm. Report zone dimensions derive from the scale; the drawing labels use metres.

BEFORE LEAVING
Verify the scale, area boundaries, exclusions and elevation units. After changing a zone, regenerate/review the layout and then its strings, MPPTs and routes. Undo can reverse the project edit; saved alternatives remain safer for major redesigns.'''),

('Layout and blocks', '''THREE DIFFERENT ANGLES
Module tilt is inclination above horizontal, such as 8 degrees. Module azimuth is its compass orientation, such as 180 degrees south. Zone layout rotation rotates the module-placement grid in the image plane. Do not change tilt to rotate a rectangle on the plan. Existing zone layout angles remain supported; there is no added zone-rotation toolbar control.

GENERATE THE LAYOUT
In Configuration or Panel, verify module width/height, gaps, edge clearances and exclusions. Choose Layout > Generate layout. The lattice rotates as a rigid grid about the zone centre; a panel is retained only when all corners fit. Inspect every zone, triangular offcuts, reserved spaces and warnings. Gaps/clearances reduce the number of modules that can fit.

EDIT EXISTING MODULES
Use the available selection/painting tools deliberately. Ctrl-click can add or assign a module; Ctrl-right-click removes one in the layout editor. When assigning existing modules, use Paint block so you do not create extra modules accidentally. Review the module count after editing. Renumber panels is explicit and can make older exported schedules obsolete.

CHANGE SOLAR ORIENTATION
Select the intended modules before applying their tilt/azimuth in Panel. With no modules selected, the panel dialog sets the default orientation. Confirm which modules have overrides before energy or weather calculations. Different orientations may require corresponding weather profiles.

INVERTER BLOCKS
Create one named block per inverter. Select its equipment row and confirm manufacturer ratings/MPPT inputs. Assign modules to the active block and place its inverter on the plan. Electrical calculations use the block's equipment relationship; a symbol or block colour alone does not supply a usable active-power rating. After equipment edits, verify the block link and diagram values.

AFTER GEOMETRY CHANGES
Generate layout again when required. Affected strings may be disconnected for review; inspect their member lists instead of assuming old electrical order is still valid. Then check MPPT assignments, update the diagram, recalculate routes and recalculate shading/energy. Existing stable module IDs do not imply unchanged physical geometry.

EXPECTED RESULT
The layout contains the intended modules only; physical-zone totals agree with the total module count; every module intended for electrical calculations belongs to the correct inverter block. No overlap or out-of-zone warnings remain unresolved.'''),

('Stringing', '''WHAT A STRING REPRESENTS
An ordered series connection, not just a coloured group on the roof. The first and last modules define the two DC route origins. The MPPT schedule and report depend on the actual saved member order.

CREATE MANUALLY
Create a string using String actions, select it in the string list and add the intended panels in electrical order. Inspect the expanded member list. Reorder modules with the available move controls or remove an incorrect member. Check that selected modules belong to the intended inverter block.

GENERATE AUTOMATICALLY
Set minimum and maximum module counts and the direction/grouping, then run the string-generation tool. Inspect the result zone by zone: a convenient geometric snake can still be unsuitable for wiring. Automatic generation is not a manufacturer design approval. Empty strings are not active strings.

CHECK EACH STRING
Confirm module count, electrical order, first/last modules, inverter block and tilt/azimuth. Resolve duplicate membership and unintended cross-block connections. Assign the intended MPPT after the string is checked. Strings of different module models or orientations need the appropriate equipment assumptions and engineering review.

SERIES VOLTAGE EXAMPLE
For 20 identical modules with Vmp = 40 V and Imp = 17.2 A, the operating string voltage is approximately 800 V and the series current remains 17.2 A. It is not 20 times Imp. These are illustrative STC values, not a cold-temperature voltage approval. Use manufacturer temperature coefficients and inverter limits for the actual check.

VIEW AND EXPORT
The report shows connections as alternating cyan/magenta lines on unfilled modules, with S1, S2, etc. identifying string numbers. Its schedule lists the exact module IDs and MPPT assignment. Use the numbered physical-block details to resolve small identifiers on the overall plan.

WHEN A STRING CHANGES
Recheck its MPPT capacity, regenerate/reflow the diagram if needed and recalculate routes: removing or moving the last module changes conductor B even when conductor A is unchanged. Recalculate affected shading/energy results before export.'''),

('MPPT assignment', '''PREREQUISITES
Every intended string has a checked member list and inverter block. Each block has the actual inverter equipment, number of MPPTs and allowed parallel string inputs. An inverter's nameplate power does not define its input voltage/current limits.

ASSIGN AND REVIEW
Select a string and the intended MPPT, or run automatic distribution. Review the assignment tree/table afterwards. Each nonempty connected string needs one assignment consistent with its inverter block. Check the number of strings on each MPPT against its configured input capacity. Automatic distribution does not prove compatible string lengths or orientations.

MANUFACTURER INPUTS
Supply maximum DC voltage, MPPT operating voltage window, maximum operating input current and short-circuit input current where applicable. Enter relevant module coefficients and site design temperatures in Configuration. Review checks labelled incomplete or missing: they are not passes.

PARALLEL STRINGS
Compare module model, length and solar orientation. Parallel string currents add at the MPPT; a series string's current does not multiply by its module count. An STC check alone cannot establish the minimum/maximum-temperature design limits.

AFTER EDITS
Changing a string, inverter block, equipment row or allowed input count can invalidate the assignment. Check for unassigned strings and removed equipment relationships, then regenerate the single-line topology and recalculate affected electrical/energy results.

EXPECTED RESULT
The assignment schedule matches the actual physical string plan and the single-line diagram. No intended active string is unassigned, no MPPT exceeds its declared input capacity and unavailable manufacturer checks remain visible.

EXPORT
Export the CSV schedule with the associated drawing. Keep the saved JSON and date/version used to produce it. Re-export after an assignment or module-number change; do not combine a new plan with an old MPPT table.'''),

('Shadow', '''PREPARE THE GEOMETRY
Calibrate the plan, check site latitude/longitude, set north correction and review each module's tilt/azimuth. Define obstacle footprints, heights and opacity. Roof elevations for shadow geometry use mm; cable elevations use m and are not substituted for them. For different roof levels, enter the relevant heights consistently.

CHECK A SINGLE SUN POSITION FIRST
Choose a date and time, preview the footprint and verify its direction against north and the image. Check that the correct roof level is affected. Wrong sun direction commonly indicates a north-reference, time-zone or date/time input problem. A footprint displaced from its real obstacle indicates geometry or scale errors.

RUN A PERIOD
Choose the period and step in the shadow simulation controls. Run it, monitor progress and use Cancel if needed. Inspect module losses, string aggregation and the most affected times. After moving modules or obstacles, changing heights/north/orientation, or opening another project, calculate again before using old results.

ANNUAL REPORT STUDY
Configuration > Annual shadow study sets the year. Engineering report export evaluates the complete calendar year in the site time zone, including leap years and real elapsed hours across daylight-saving changes. The report includes a spatial module-loss heatmap, daily/hourly heatmap and monthly energy/loss table.
This study uses the project's clear-sky and selected shading/thermal assumptions. It is separate from the weather-based Energy/BESS comparison, even when both use the same calendar year.

READ THE HEATMAPS
Spatial heatmap: colour is each module's energy-weighted annual loss, not its loss at one chosen instant. Calendar heatmap: colour is loss for a local hour/day; blank cells have no unshaded generation. Compare colour-bar limits before comparing different projects. Monthly loss percentage is lost energy divided by unshaded potential, not a simple mean of percentages.

MODEL ASSUMPTIONS
Opacity represents the declared fraction blocked. The geometric model and optional bypass estimate do not reproduce full I-V behaviour, mismatch, optimizers or an independently validated bypass-diode model. Review obstacle dimensions, temperature assumptions and solar source before interpreting the result as an engineering estimate.'''),

('Spreadsheet', '''PURPOSE
Use the sheet for project quantities and transparent derived calculations. It does not automatically validate a user's engineering assumptions. Add a description and unit for each numerical quantity.

INSERT VARIABLES
Select a cell, then search the variable explorer. Double-click a variable or use Insert to insert its identifier. Use the available explorer names rather than guessing. Equipment records are edited in Configuration, not in the variable sidebar.

SUPPORTED FORMULAS AND EXAMPLES
Start with =. Cell references and +, -, *, / with parentheses are supported. SUM is the supported aggregation function; do not assume arbitrary Excel functions are available.
=PV_CAPACITY_WP/1000 gives the global reference DC capacity in kWp.
=B15*ZONE1_PANEL_COUNT multiplies the value in B15 by actual modules in Zone 1. If B15 is kg/module, the result is kg.
=SUM(B4:B12) sums the specified cells.
=TOTAL_CABLE_WEIGHT_KG reads the declared current cable-inventory mass when it is available.
Equipment formulas can reference equipment cells and project variables. The global PV capacity uses the reference module equipment row; review that convention before relying on it for a mixed-module project.

EDIT AND COPY
Select a cell to inspect/edit its formula. Select a range and use Ctrl+C/Ctrl+V. Drag the fill handle to copy formulas; relative references shift with the destination. Review a copied formula before trusting an entire filled column. This is not a full Excel-compatible calculation engine.

ERRORS AND EMPTY CELLS
#ERR means the expression or one of its inputs cannot be evaluated. Check spelling, available variables, supported operators and missing engineering inputs. #CIRC! means references form a cycle; remove the circular dependency.
Some arithmetic/range operations treat blank or nonnumeric cells as zero. Therefore a plausible total does not prove that every required value was entered. Unknown engineering quantities, such as cable mass, must not be replaced with 0 merely to clear an error.

EXPORT AND REPORT
Save the JSON to preserve formulas and project relationships. CSV export is a table exchange format and does not preserve the full interactive project. The engineering PDF fits the complete configured sheet on one page, including empty cells; formula cells show their evaluated values as well. Very large sheets may need substantial scaling. Review legibility in the exported PDF.'''),

('Electrical single-line diagram', '''PREREQUISITES
Finish string/MPPT assignments and check inverter equipment first. The automatic drawing reflects those assignments; rearranging a symbol does not change the underlying electrical connection schedule.

GENERATE
Auto generate builds Strings -> MPPT -> Inverters from the project. Inverter groups have naturally ordered strings and separate lanes. Inspect unassigned or custom elements before issuing a drawing. Missing equipment data remains missing rather than becoming a manufacturer's default.

NAVIGATE AND ARRANGE
Hold the left mouse button and drag the drawing to pan. Right-click an element to select it. Hold the right mouse button and drag from empty space to draw a selection rectangle; Shift/Ctrl extends selection. To move selected elements, right-drag from an already selected element. The side list also supports multiple selection. Click Fit diagram to fit the complete drawing in the canvas. Click Reflow diagram to restore automatic spacing. Show electrical values displays the available electrical ratings inside the elements and can adjust their spacing.

CABLE DISTANCES WITHOUT WAITING
Opening or generating the diagram does not calculate cable routes. A link displays A+B only when current saved routes are available. If it displays Calculate routes in Cabling, open Cabling, enter the required paths and elevations, then calculate or refresh routes. Return to the diagram to see the updated distances. After changing geometry, equipment or sizing inputs, recalculate routes. Module chain length is the approximate panel-to-panel sequence length; it is different from the two string-to-inverter conductors.

CUSTOM DEVICES AND LINKS
Add the required custom protective devices, meters or switchboards. Choose a link style, then click its two endpoints. Edit the appropriate equipment/electrical inputs in Configuration. A custom symbol or connection records the drawing decision; it does not calculate or certify the device's protection coordination.

DELETE AND REGENERATE
Delete removes selected diagram elements and their links. Automatic elements may return when regenerated from the source strings/assignments. To remove their underlying electrical role, edit the source string or assignment too. Before regenerating a carefully arranged drawing, save a checkpoint.

REVIEW IN THREE PLACES
Compare the string member schedule, MPPT assignment and diagram. The string count, inverter groups and relevant electrical values must agree. Check the meaning and unit of distance labels against current cable calculations. Missing/stale lengths are not valid zero lengths.

EXPECTED RESULT
No overlapping labels, omitted intended strings or unexplained unassigned devices. Equipment and protection values are explicitly entered, and custom content is reviewed. The drawing remains a project representation rather than a manufacturer-approved wiring diagram.'''),

('Cabling', '''PREREQUISITES
A calibrated plan; checked ordered strings; inverter block/equipment and location; routing paths/areas; cable elevations for every crossed surface; inverter terminal height and reserves. Review string-specific operating current/voltage and manufacturer cable inputs in Configuration.

DEFINE THE PHYSICAL ROUTE
Draw cable tray polylines; right-click finishes. Define gathering points at the intended zone exits and suitable routing polygons. Place the inverter for each block. Calculate routes, then inspect the route method: the router prefers the drawn network, otherwise routing-area paths, then an estimated direct L-shaped fallback. A fallback is a calculation assumption that needs physical site review.

A AND B ARE SEPARATE CONDUCTORS
A starts at the first module; B starts at the last module. Both terminate at the inverter. Solid and dashed lines distinguish conductors in exports. The loop inventory is length A + length B, not twice one convenient path. Reordering a string can change both origins.

HOW LENGTH IS BUILT
Each conductor length = planar path + vertical steps + terminal reserve. Surface boundaries split the path; elevation changes are counted along it. A gap within the maximum supported bridge length retains the upstream height until the next surface. A longer unsupported gap descends to the ground datum and rises again. The default bridge threshold is zero; set a nonzero value only for a real supported crossing. Missing or conflicting heights block affected routes.

PER-STRING SECTION
Calculate routes fills String sizing. Check A/B/loop lengths, operating current, total string voltage, proposed or chosen section, voltage drop, mass and status. Module Imp and Vmp with the string module count provide operating inputs when the relevant module equipment is available. Use per-string overrides when they differ or are unavailable.
The proposal uses DC-loop voltage drop. Enter corrected cable ampacity and the protection rating to enable their available comparison. Neither the proposed section nor an entered ampacity check replaces review of installation method, thermal conditions, grouping and protection design.

MASS AND SCOPE
Enter kg/m for the actual cable section from manufacturer data, or an explicit per-string value. String mass = A+B length times kg/m. TOTAL_CABLE_WEIGHT_KG includes active DC string-to-inverter routes plus additional declared cable-inventory entries. Unknown required route/mass data makes the total unavailable; the known subtotal is not the complete total.
Inter-module, AC and accessory cables are outside the automatic route inventory unless explicitly entered as additional cables. Do not count a cable both automatically and in the additional inventory.

WHEN TO RECALCULATE
After module/end-point/order changes, inverter moves, path/area/elevation/reserve changes, sizing overrides or cable-data changes. Export only current results. An empty route or missing value is not a zero-length cable.'''),

('Energy / BESS', '''GOAL
Compare the same connected PV installation and load without storage, with one cabinet and with two cabinets. Inspect useful PV supplied to the load, grid purchases, exports, curtailment and battery losses separately.

COMPLETE THE INPUTS
Import consumption for the period. Review source units, missing values and the time convention. Import suitable weather or explicitly accept the clear-sky estimate. Verify inverter active power or kVA plus power factor, string connections, module orientations, site/time zone and AC conversion factor.
Enter cabinet capacity, charge/discharge limits, SOC limits and round-trip efficiency. Configure the export limit, battery auxiliaries and any degradation assumption used. Defaults are assumptions to review, not measured site values.

CALCULATE ONCE
Use Calculate 3 options. The calculation runs in the background; watch progress and use Cancel calculation if needed. PV supplies the load first. Surplus charges the battery within power/SOC limits. Remaining surplus is exported within the grid limit and then curtailed. The battery supplies remaining load deficit; the grid supplies the rest.
Initial SOC is minimum SOC. Two cabinets double capacity while sharing the configured charge/discharge power limits. The model does not double those limits merely because there are two cabinets. It does not simulate grid charging, tariff arbitrage or ancillary-service income.

READ THE CHARTS
Annual load-supply stack: direct PV + battery discharge + grid import. Each scenario serves the same load. A separate PV-use view shows charging, exports and curtailment. Charging is not all useful self-consumption: some energy is lost or remains stored.
Daily chart: load sources, PV uses and a separate SOC panel. Choose the date/configuration; Previous day / Next day moves through the profile. Click a bar for exact hourly values. SOC is shown at interval boundaries on a 0-100% axis.
Monthly charts use MWh; annual tables commonly use kWh. Month labels include the year. Check the displayed unit before comparing values.

CHECK THE BALANCE
Load must equal direct PV + useful battery discharge + grid supply under the displayed model. Check auxiliary consumption separately where reported. Compare charging, discharge, losses and change in stored energy. A different final SOC can affect the apparent benefit over a short period; inspect initial/final SOC instead of comparing discharge alone.

ECONOMICS AND PERIOD
Results > Economics uses entered tariffs/investment and the model's available cost/discount assumptions. Review maintenance, degradation/lifetime and discount inputs where shown; taxes, financing, replacement costs and hourly tariff optimisation are not inferred. Payback is withheld for partial-year consumption rather than annualising it silently.
Totals describe the imported period. A TMY weather source is typical-year weather, not measured historical weather for those consumption dates. Changing relevant inputs invalidates results; calculate again before using the comparison or exporting it.'''),

('Files and weather', '''HOURLY CONSUMPTION CSV: RECOMMENDED FOR EXACT TIMESTAMPS
Use a comma-separated UTF-8 file with exactly named input columns:
timestamp,consumption_kwh
2026-01-01T00:00:00+01:00,12.5
2026-01-01T01:00:00+01:00,11.8
2026-01-01T02:00:00+01:00,10.9
These three rows demonstrate the format; they are not a complete-day or annual profile. Supply the complete consecutive hourly sequence required for your study. Values are nonnegative interval energy in kWh, with a decimal point. Do not supply cumulative meter readings or instantaneous power without first converting them correctly.
UTC offsets are required, including the appropriate offset across daylight-saving changes. Distinct offsets distinguish repeated local clock hours. The importer checks the timestamp sequence. Do not use the 24-slot/day Excel format to encode an actual 23- or 25-hour day.

DAILY CONSUMPTION EXCEL
The active worksheet needs headers: date, day, 0, 1, ..., 23. Use real Excel dates in the first column and consecutive dates. Hours 0-23 contain numeric kWh, not text with unit suffixes. The legacy data/giorno headers are also accepted. Formula cells must have usable saved calculated values when read by the importer.
This format always represents 24 slots per day. Choose the missing-value method in Configuration: Previous week average, Reject missing values or Fill with zero. Review the imputed count and affected periods; zeros and averages can materially change BESS results.

IMPORT ORDER
Set site, time zone and module orientation. Import consumption first, then weather. Replacing consumption removes its old weather association. Configuration source selectors accept a consumption file and weather JSON; leaving a selector empty retains the loaded source.

HISTORICAL WEATHER JSON
The supported Open-Meteo format supplies hourly irradiance and temperature compatible with the consumption period. Verify source latitude/longitude, tilt and azimuth metadata against the actual source file. The app's prompt/default metadata is not evidence that the file was generated for this project. Different module orientations need corresponding compatible weather profiles.

PVGIS TMY JSON
Import the original PVGIS TMY JSON. A typical meteorological year combines representative weather; it is not the measured weather of the selected consumption year. The importer projects the available irradiance components for the declared module orientations. Check the reported provenance and any missing-data message before calculating.

IF IMPORT FAILS
Correct the file identified by the message: headers, missing offsets, timestamp gaps/duplicates, nonnumeric/negative values, unsupported JSON structure or insufficient weather coverage. Reopen the importer after correction. Do not rename an unrelated JSON as weather data or substitute invented metadata to bypass a mismatch.'''),

('Reports and exports', '''BEFORE EXPORTING
Save the project under its intended filename. Check actual module count, scale, assignments, equipment relationships, cable statuses, weather/consumption period and calculation provenance. Review missing inputs explicitly. The PDF title is the save filename with underscores converted to spaces and .json removed; changing only the PDF output filename does not rename the project.

ENGINEERING REPORT PDF
Home > Engineering report PDF creates a standalone PDF report, including vector plans, technical tables and calculation snapshots. No LaTeX file is generated.
The report includes source roof plan, numbered layout, string lines/numbers on unfilled panels, string/MPPT schedules, zone dimensions, technical/equipment records, annual shading heatmaps/tables, per-string cable drawing and sizing, available Energy/BESS comparisons, the complete spreadsheet and physical-block details.
Text is black with Times New Roman where installed and a Times-compatible fallback elsewhere. Colour is reserved for meaningful drawings/charts. Physical-block details do not repeat modules across arbitrary overlapping tiles. Zone layout rotation is distinguished from module tilt.

WHAT IS RECALCULATED
The annual shadow study uses the configured year. The report works on a frozen project snapshot and can recalculate stale Energy/BESS results when its required data is complete. Export does not invent missing inverter power, weather, cable mass or consumption. Unavailable calculations are explained. No illustrative prototype BESS values are inserted into real project reports.

SPREADSHEET AND EQUIPMENT
The complete sheet fits on one page, including all configured cells; formula results are visible. Large sheets can become too small to read: inspect the PDF and use the companion CSVs when necessary. Equipment formula fields show evaluated values in the report; raw project inputs remain available in the snapshot for traceability.

JPG
Project > Export final JPG exports the complete plan, rather than only the current viewport. A high-resolution export cannot add survey detail that is absent from the original image. Inspect numbering, line/label readability and whether the intended drawing layer was selected. The JSON remains the editable source.

CSV AND VECTOR ASSETS
MPPT/string schedules and hourly energy exports serve different purposes. Do not interchange them. CSV does not contain all project relationships. Vector PDF/SVG plans preserve drawing sharpness and module identifiers when zoomed.

FINAL REVIEW
Open the exported files. Confirm title, date, scale, module/string counts, units, source period, missing-data notes and readable labels. Keep a matching saved JSON so the result can be reproduced. Re-export after changes; avoid distributing schedules from one project state with drawings from another.'''),

('Troubleshooting', '''CONFIGURATION WILL NOT APPLY
Read the field named in the message. Check required blanks, numeric format, units, nonfinite values and allowed choices. Uncheck Required fields only if the relevant optional field is hidden. File imports may also fail during Apply; check their structure. Correct the draft and retry; do not replace missing ratings with arbitrary numbers.

TOO FEW OR TOO MANY MODULES
Verify the image calibration, module dimensions, gaps, edge clearance, exclusions and complete-corner containment. Review manually added modules. The filename is not a reliable module count: an old filename can disagree with the current project. Compare actual module count and zone variables.

A STRING DISAPPEARED OR NEEDS REVIEW
Geometry edits can invalidate its members. Inspect the current physical modules, rebuild the intended member order, then assign its MPPT again. Recalculate cabling and energy afterwards. Undo can restore a recent change within the same session.

ENERGY CANNOT BE CALCULATED
Check consumption first; then module/equipment values, layout warnings, connections and inverter active power. Enter kW, or kVA with an actual power factor. Verify the time zone, orientation-specific weather and coverage. Complete BESS numeric limits and the AC conversion factor. A missing rating is not a reason to select a generic inverter power.

OLD ENERGY CHARTS ARE HIDDEN
This is expected after changing relevant inputs or importing a legacy result without current provenance. Calculate 3 options again. If weather metadata became incompatible, load a compatible source before recalculating.

CABLE ROUTE OR LENGTH IS UNAVAILABLE
Check active strings and both end modules, their blocks, inverter position, geometry scale, routing surfaces and every crossed elevation. Resolve missing/conflicting heights. Inspect the fallback method rather than accepting a direct estimate as a surveyed route. Recalculate after correction.

SECTION EXISTS BUT THE CHECK IS INCOMPLETE
A voltage-drop proposal can exist without corrected ampacity/protection data. Enter the actual corrected ampacity and applicable protection rating; review the displayed status. Changing the chosen section can make voltage drop exceed the target. A proposal alone is not a complete cable design.

TOTAL_CABLE_WEIGHT_KG IS UNAVAILABLE
Check every active string's current route and section, plus kg/m for that section or its override. Check additional inventory length, quantity and kg/m. A known subtotal can coexist with missing records. Do not enter zero weight simply to make the total available.

CSV OR WEATHER IMPORT FAILS
Use Files and weather for the exact formats. Common causes: semicolon-delimited consumption CSV, missing UTC offsets, missing hours, duplicate instants, decimal commas, text units, unsupported JSON or inadequate weather coverage. Excel needs actual dates and numeric hourly cells.

SPREADSHEET #ERR / #CIRC!
Inspect formula text and variable spelling. Only use supported functions/operators. Remove circular references. Check whether an engineering variable is unavailable. Blank/non-numeric values may be treated as zero in some calculations, so a numeric result still requires an input completeness check.

PDF EXPORT FAILS
Wait for another task to finish. Select a writable destination and close an existing PDF if its viewer locks the file. Read the actual error message; missing calculation data should be reported within the export, not fabricated. Keep enough space for the PDF, .tex and assets. If a code error persists, retain the JSON and report the exact message and action that triggered it.

PROGRESS OR UNDO IS DISABLED
A background calculation may still be active. Use its cancellation control and wait for completion. Avoid starting repeated copies of the task. Undo is also unavailable at the beginning of history; Redo is unavailable after a new edit or project load.'''),

('Glossary', '''PHYSICAL ZONE / PHYSICAL BLOCK
A bounded installation area on the roof. Report block B1, B2, etc. identifies such physical groups; these are different from electrical inverter blocks.

INVERTER BLOCK / MPPT / STRING
Inverter block: modules/strings associated with one inverter. MPPT: an inverter input tracker with manufacturer limits and allowed string inputs. String: modules connected in series in a saved order. Several compatible strings can share an MPPT where the declared input capacity permits it.

MODULE ID / STRING ID
Module IDs identify actual panels and appear in the numbered layout/member schedules. S1 denotes String 1 in the report. Renumbering changes display IDs and requires new matching exports.

LAYOUT ROTATION / TILT / AZIMUTH
Layout rotation: image-plane placement angle. Tilt: inclination above horizontal. Azimuth: compass direction. They affect different geometry/calculations and cannot substitute for one another.

STC / Pmax / Voc / Vmp / Isc / Imp
STC is the datasheet reference condition. Pmax is rated maximum module power. Voc is open-circuit voltage; Vmp is operating voltage at maximum power. Isc is short-circuit current; Imp is operating current at maximum power. Actual operating/temperature values differ from STC values.

W / kW / kWp / kWh / kVA
W and kW are power; 1000 W = 1 kW. kWp is PV reference nameplate power. kWh is energy over a period. kVA is apparent inverter power and does not automatically equal usable active kW.

SOC / ROUND-TRIP EFFICIENCY
SOC is battery state of charge. The configured usable window is between minimum and maximum SOC. Round-trip efficiency relates charging to recovered energy under the selected model; auxiliaries and terminal stored-energy changes must be inspected separately.

DIRECT PV / USEFUL SELF-SUPPLY / EXPORT / CURTAILMENT
Direct PV supplies the load without storage. Useful battery discharge also supplies the load. Export leaves the site through the grid connection. Curtailment is PV energy not used, stored or exported under the model's limits. Battery charging must not be counted again as useful load supply.

TMY / CLEAR SKY / HISTORICAL WEATHER
TMY is representative typical-year weather. Clear sky is a modelled unclouded irradiance estimate. Historical weather corresponds to an actual dated source. State which method produced the result before comparing projects.

A+B LOOP / AMPACITY / LINEAR MASS
A and B are separate string-to-inverter conductors. Loop length is their sum. Corrected ampacity is allowable current after the declared installation corrections. Linear mass is kg per metre of the actual cable, not conductor density or kg per coil.

CURRENT / MISSING / FAILED CHECK
Current means results match the tracked inputs. Missing means required data is absent. A failed check reports an implemented comparison that did not pass. Neither a current result nor absence of software warnings establishes a complete engineering certification.'''),
]
