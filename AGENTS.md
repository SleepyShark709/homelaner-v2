# Project scope

## Current phase (2026-10-25): original-game restoration only

Restoring UNDEFEATED is the only active primary milestone. The Homelander skin, free-destruction mode, heat vision and other Web-side extensions are frozen optional experiments; they must not be treated as completion evidence or expanded until the restoration gates pass:

1. Capture the real gameplay player/camera transform from the original executable (not the menu Pawn).
2. Re-render the same location/camera and record an honest same-camera comparison.
3. Close the lighting/material/sky/scene-content gaps and restore the missing props.
4. Verify the original animation/state logic, then preserve it on any replacement character.

Status (2026-10-25): gate 1 complete via `WBP_TitleSinboard_C:GameStartEvent()` + one `InputDone()`; the settled gameplay transform is `pawn (-311.999, 7473.891, 167.150)` / `cam (-361.999, 7073.891, 327.150)`, rot `(-10, 90, 0)`. Gate 2 has a first same-camera comparison at `(-3.12, 74.73891)` with camera `(-3.62, 3.2715, 70.73891)`, measured FOV 90 (`PlayerCameraManager:GetFOVAngle()`); the default play camera now uses 90 too. Gate 3 is in progress: the storefront `-Window_mat` and `Tilable_metal_TintC_Inst` now use their recovered colour/tint parameters instead of the neutral fallback; the original 1024×1024 `T_StaticMinimap_Tex`, `map250` ink frame and `T_PlayerIcon` are wired as the default HUD with the recovered `WorldOrigin/BoxExtent` mapping (`?hud=help` restores the authored panel), but the state-driven green/red tint is only an authored outer-rim preview (generated from the map250 alpha), and the nearest-8 quest icon layout is a preview, not the original active-quest icon state machine or scaling material. Lighting, contact shadows, remaining HUD elements and materials are still open. `?ssao=0` disables the default preview SSAO, which combined with exposure .55 matches the same-camera original's measured mean luma 55.8 / std 31.3 (Web 55.6 / 30.1); this is a screen-space preview, not an original AO/lightmap reconstruction. A `LightingTest` postprocess probe recorded AutoExposure 1..8 and Bloom 2.5, but those values are not MainLevel baked lighting and a Bloom preview was rejected for adding non-original edge glow. The default play view uses a preview exposure calibration of 0.55 (`?exposure=1` disables it); together with the preview SSAO the measured same-camera luma is Web 55.6 / std 30.1, not a recovered UE auto-exposure/tone curve or AO/lightmap. Gate 4 remains open. The original `HeroAnimBP` and `HeroABS_MoveGround/Flying/JumpFallLoop/AirAttack` assets are now decoded and their real state/clip references are documented in `docs/animation-state-recovery.md`; Web now imports ten original locomotion clips and uses `Hero_SprintRun` for run / `Hero_JumpFall` for jump; the imported `Hero_SprintSuper` sample was rejected for normal running after visual inspection; the remaining gap is BlendSpace/transition/notify/root-motion state logic, not the raw clips.

## Durable handoff (2026-10-25, before power-off)

The complete remaining-work checklist is [docs/todo-restoration.md](docs/todo-restoration.md). Read that first; this section preserves the facts that are expensive to rediscover.

### Verified original-game runtime

- Original install (read-only): `E:\SteamLibrary\steamapps\common\UNDEFEATED`.
- UE4SS staging procedure: `tools/runtime/ue4ss/README.md`. The temporary staging copy is under `C:\Users\Shark\AppData\Local\Temp\undefeated-ue4ss`; rebuild it if removed.
- Do **not** use `ClientTravel("MainLevel")` or `ConsoleCommand("open MainLevel")`; both were rejected by the game.
- Enter real gameplay by calling the title Blueprint event:

  ```lua
  local title = FindFirstOf("WBP_TitleSinboard_C")
  title:GameStartEvent()
  -- wait for the intro to begin, then exactly once:
  title:InputDone()
  ```

  Calling `InputDone()` repeatedly keeps advancing/looping the intro. After one call, wait; do not automate more input.
- Settled gameplay transform (measured):

  ```text
  pawn = (-311.999, 7473.891, 167.150) cm
  cam  = (-361.999, 7073.891, 327.150) cm
  rot  = (-10, 90, 0)
  fov  = 90.000   (PlayerCameraManager:GetFOVAngle)
  ```

- Web same-camera conversion (x/100, z/100, y/100; yaw = 90 - UE yaw):

  ```text
  player = (-3.12, 1.6715, 74.73891) m
  camera = (-3.62, 3.2715, 70.73891) m
  ```

  Exact inspection URL: `?view=play&startup=1&at=-3.12,74.739&yaw=0&exact=1&cam=-3.62,3.2715,70.739&camyaw=0&campitch=-0.1745&fov=90`.

### Current Web play defaults

- Default `?view=play` is the original character/slice; default camera FOV 90.
- Default HUD is the recovered original minimap stack (`T_StaticMinimap_Tex`, `map250`, `T_PlayerIcon`); `?hud=help` restores the authored inspection panel.
- Minimap world mapping from `BP_WorldCaptureCamera`: `WorldOrigin=(-130000,-130000) cm`, `BoxExtent=(130000,130000) cm`, `OrthoWidth=260000 cm`; texture covers `[-1300,1300] m`.
- Default preview exposure `.55` and default preview SSAO (`.9`) are **calibration**, not original UE auto-exposure/AO/lightmap. Disable with `?exposure=1` / `?ssao=0`.
- Minimap outer-rim green/red tint and nearest-8 quest icons are authored previews, not the original `M_MiinMapChangeVisualizer` active-quest state machine.
- Recovered storefront materials: `-Window_mat` (dark blue-black, roughness .0622, emissive .15) and `Tilable_metal_TintC_Inst` (recovered tint); do not revert to neutral fallback.

### Known current state / next task

- Gate 1 (real gameplay transform) and Gate 2 (same-camera position/rotation/FOV) are complete.
- Gate 3 (lighting/material/sky/scene/HUD equivalence) is incomplete: MainLevel lightmaps/auto-exposure/Bloom, awning/stone shading, full HUD/state tint/icons remain. `MainLevel_BuiltData` is confirmed to contain 464 LightMapTexture2D + 198 ShadowMapTexture2D; inventory in `research/world-recovery/lightmap-inventory.json` and notes in `docs/lighting-recovery.md`. The per-component LightMapIndex/UV and mesh UV1 binding are still unresolved, so the lightmaps are not applied yet.
- Gate 4 is incomplete. Ten original locomotion clips (`Hero_Walk`, `Hero_SprintRun`, `Hero_SprintSuper`, `Hero_JumpSpeed`, `Hero_JumpLand`, `Hero_JumpFall`, `Hero_JumpFallFast`, `Hero_StartSprint`, `Hero_Stopping_Sprint`, `Hero_Stopping_WalkRun`) are now appended to the 93-bone hero (28 clips total); low-speed ground motion uses `Hero_Walk`, run uses `Hero_SprintRun` (the imported SprintSuper sample was rejected for normal running after visual inspection), jump uses `Hero_JumpFall`. A basic direct chain is implemented: low-speed grounded motion uses `Hero_Walk` (<4 m/s), `Hero_SprintRun` above that, `StartSprint→SprintRun`, `SprintRun→Stopping_WalkRun→Idle`, `JumpSpeed→JumpFall→JumpLand` (timed by `AnimationGroup.getLength()`). The `HeroABS_MoveGround` BlendSpace axes, exact AnimBP transition/blend times, `ALS_N_Jump`, flying blendspaces and AnimBP notify/root-motion logic are still not implemented.
- The immediate next implementation step is 2.2 in the TODO: implement the recovered `HeroAnimBP`/`HeroABS_MoveGround` state machine and its transition/blend timings; do not substitute another clip. The import report is `research/world-recovery/locomotion-import.json` and the importer is `scripts/append-locomotion-animations.py`.

### Commands / constraints

- Use bundled Node 24; system Node 18 fails:
  ```powershell
  $env:PATH = 'C:\Users\Shark\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin;' + $env:PATH
  npm run typecheck
  npm run build
  npm run capture:play
  ```
- Original/derived assets stay local and Git-ignored (`public/assets/world`, `character`, `animated`, `research/exports`, decoded dirs). A clean checkout needs the local asset pipeline before rendering.
- Same-camera evidence: `research/runtime-observation/comparison-live-gameplay-start-final.jpg`; original capture: `research/runtime-observation/original-gameplay-start-final.png`.
- Do not call this a complete port or visual equivalence; Gate 3/4 and full gameplay remain open.

Until those gates pass, do not call this a faithful port or a successful migration. The current default `?view=play` is the original character/slice; `?skin=homelander`, `?mode=free` and `?retarget=1` are experimental and may be incomplete.

This is a new independent project at E:/undefeated-web. Do not base implementation on the existing homelander-simulator source tree. The original game installation is read-only.

User correction (2026-10-24, supersedes milestone shortcuts): the user requires comprehensive REA-led reverse engineering and faithful original-game reconstruction. They rejected the current small browser demo as insufficient. Suspend further sandbox/free-mode/model development until original-world coverage, materials, animation/state logic and runtime comparison are evidenced. Preserve the current demo, but label it a partial reconstruction, never a complete port. Do not use self-designed approximate systems as replacements for unexamined original behavior. Actual REA output, UAssetAPI/UModel output and authored Web code must have distinct provenance. A recovered asset sample is not whole-game coverage. Restore the original game before pursuing the requested modifications.

User's accepted direction:
1. Reconstruct UNDEFEATED for browser-local execution, preserving original appearance, skeleton, animation and behavior where conversion is feasible.
2. Add hold-E heat vision as an additional input; keep original right-button ranged attack. Resolve E's original ascend conflict.
3. Add free destruction for people, vehicles and designated props; remove player damage, negative score, degradation, involuntary control loss, ability resource limits and forced failure in this mode.
4. Only then replace the protagonist's appearance with Homelander. Prefer retaining the original skeleton and animations; adapt/re-skin the replacement mesh when needed. Do not assume Homelander's existing rig must be retained.

Current stack: Babylon.js + TypeScript + Vite, local-only. Physics for later gameplay is a separate implementation decision; there is no physics engine dependency in the asset laboratory yet.

Keep original/derived game assets local and excluded from Git. Maintain source identity and conversion manifests. Treat recovered strings, bytecode, default values, runtime observations and new design choices as distinct kinds of evidence.

Do not call an asset viewer or greybox a complete game port. Missing original assets must remain explicitly documented. Validate imports, animation, scale and visual output before making completion claims.

Use npm scripts with Node >=24 (native TypeScript execution in movement tests); scripts/dev.ps1 can use the existing bundled Node runtime without changing global configuration. Check type safety, build and meaningful asset integrity checks. Keep development servers bound to loopback.

Current default is the original-world recovery viewer (src/world.ts, src/world/). It consumes geometry/material/terrain manifests in public/assets/world; original scene inspection only, not restored gameplay. Old playable prototype is ?view=prototype; original character/animation lab is ?view=assets. B1/B2/B3 playable slice is ?view=play: original character + ResidentialArea1 + full-resolution heightfield + 29 recovered /Mesh/Floor/ AABB tops + AABB collision proxy + original-input movement + preview population + original combat animation/projectile timings + dynamic all-actor collision. A ?district=<level> query loads MainLevel + that main-world district for inspection; ?at=<x,z>&yaw=<rad> places/orients the viewer-safe spawn on a recovered floor for inspection; preview population remains ResidentialArea1-only. CommercialArea around (91,181) is an unproven start-plaza candidate (stone balustrades/facades/benches with native brick paving now materialized), not a matched camera. Spawn search now rejects points whose 4 m rear camera slot intersects the static AABB set, so the candidate plaza pose does not force the camera into the character. An optional ?population=original mode places 6 recovered BP_CharaSpawnPoint citizens outside a 10 m player radius (18 m spacing) with routes from nearest recovered BP_CharaChildWaypoint positions (same parent where available); it is inspection-only because the original spawn rhythm/navigation, traversal and spline transform are unresolved. The old prototype district-local spawn/population positions are shifted by originUE (-100,-550) m into the restored ResidentialArea1; the spawn is still not a proven original PlayerStart. Population placements are from the prior prototype; citizen routes use nearest recovered BP_CharaChildWaypoint positions when the generated manifest exists, but route order/traversal, navigation and AI are still preview; free-mode defeated citizens revive after 8 s as a preview lifecycle, not recovered spawner cadence; vehicles hold behind a vehicle up to 7 m ahead and yield to the player up to 5 m ahead as authored preview rules, not the BP_TrafficSystem state machine; combat uses baseline damage (strong vehicle only) by default; an optional ?mode=free uses FREE_RULES for citizen/vehicle/prop destruction, with citizen respawn after 8 s; ?traffic=1 draws 227 recovered CrossWalk placement rings and a nearest-crosswalk HUD distance; 339 TrafficLight mesh positions are exported but signal timing/BP_TrafficSystem behavior is not recovered. ?quests=1 visualizes 21 recovered FireQuest_BP/MatQuest_BP trigger positions with orange/blue rings, marks proximity discoveries (x/21) and shows an F detail hint; quest state machines, completion and rewards are not recovered. ?skin=homelander loads the user-provided homelander.glb (real mesh/textures/skeleton) and maps Homelander's authored idle/run/fly/punch/combo clips onto the original action names; the original hero skin still uses the original 18 clips. ?retarget=1 is an experimental original-clip retarget that leaves arm deformities and is off by default; exact frame-for-frame original motion on the Homelander rig is not solved. The original CitizenWayPoint network is audited but not wired because actor/component outer links and spline coordinate transforms remain unresolved. A first non-matched original-vs-Web character/camera/lighting comparison is recorded in docs/runtime-comparison.md; it is not same-camera or pixel equivalence. Jump/gravity and AABB/camera collision are approximations, so it is not the complete original gameplay baseline. Read docs/playable-baseline.md for its evidence and gaps, docs/world-recovery.md for world evidence, and docs/progress.md for historical prototype work. Keep template defaults distinct from executed construction scripts, static all-level views distinct from runtime streaming, and projected materials/preview lighting distinct from original shaders/rendering. Asset and source counts are not whole-game completion percentages.

Pass 2 defaults to streaming-manifest's 17-package startup baseline. SM_Floor12000x15000, Bench and nearby Tree/Palm thin instances are materialized as regular mesh clones at load, so native MI_FloorBrick1 paving, benches and local trees render; ?floors=overlay remains an optional authored GroundBrick_B_A fallback. This is a static snapshot, not an executed streaming state machine. Preserve recovered shader contracts (run restore-evidenced-shaders.py after older material pipeline steps). All 46 known socket gaps now have reference-pose transforms; animation following remains unimplemented. Empty MID sharing is restricted to identical rendering definitions with no own overrides or unknown properties; runtime mutations must fork material instances. Original executable was observed at title/menu/start plaza only; no matched-camera or movement equivalence has been established. Consult research/runtime-observation/report.zh-CN.txt and browser-validation-pass2.json.
