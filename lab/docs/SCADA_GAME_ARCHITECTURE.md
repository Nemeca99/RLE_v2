# RLE SCADA Game-Like UI Architecture

**Status**: Phase 1 & 2 Core Complete  
**Date**: 2025-10-30  
**Version**: Foundation

## Overview

Game-like navigation system for RLE monitoring with 2D grid world, scene management, and multi-input support. Built on foundation of corrected pygame SCADA v1/v2 dashboards.

## Architecture

### Scene System

```
SceneManager (stack)
├── BaseScene (abstract)
├── GridScene (2D world selector)
├── LiveScene (real-time monitoring)
├── ReplayScene (historical playback)
└── StartScene (main menu, optional)
```

**Navigation:**
- `mgr.switch(scene)` - Replace entire stack
- `mgr.push(scene)` - Add to top (enter portal)
- `mgr.pop()` - Remove top (ESC back)
- `mgr.scene` - Current active scene

### Grid World

**Features:**
- 10x8 cell grid (640x512 pixels)
- Colored portal cells for devices/modes
- Player position (green cell) with keyboard navigation
- Mouse hover tooltips (0.3s delay)
- Click-to-enter portals
- Keyboard repeat: 0.2s delay, 0.05s interval

**Portals Defined:**
- GPU Monitor (3,2) - Green, device=gpu
- CPU Monitor (6,2) - Blue, device=cpu  
- Replay Session (3,5) - Orange, mode=replay
- Archive Replay (6,5) - Dark orange, archive=true

### Input Methods

**Keyboard:**
- Arrow keys / WASD: Move player
- Space: Enter portal at player position
- ESC: Navigate back / quit

**Mouse:**
- Hover: Show tooltip after 0.3s
- Left-click: Enter portal immediately

**Touch:**
- Tap: Enter portal
- Long-press (0.4s): Show tooltip

### Integration Points

**Scene Constructors:**
```python
# LiveScene factory
def make_live_scene(portal_metadata, mgr):
    return LiveScene(mgr, portal_metadata)

# ReplayScene factory  
def make_replay_scene(mgr):
    return ReplayScene(mgr)
```

**Portal Metadata:**
```python
{
    "name": "GPU Monitor",
    "device": "gpu",           # or "cpu"
    "mode": "replay",          # optional
    "color": (0, 255, 0),      # RGB portal color
    "csv_dir": "lab/sessions/recent"
}
```

## File Structure

```
lab/
├── scene_manager.py          # Scene stack manager
├── base_scene.py             # Abstract scene base
├── grid_config.py            # Grid/portal configuration
├── grid_scene.py             # 2D grid world implementation
├── live_scene.py             # Live monitoring wrapper
├── main_scada_game.py        # Main entry point
├── RUN_SCADA_GAME.bat        # Launcher
├── pygame_scada_v2.py        # Existing SCADA (corrected)
└── docs/
    └── SCADA_GAME_ARCHITECTURE.md  # This file
```

## Current Status

### ✅ Completed

**Phase 1: Core Architecture**
- [x] SceneManager with stack-based navigation
- [x] BaseScene abstract class
- [x] Grid configuration system
- [x] Main game bootstrap launcher

**Phase 2: Grid World**
- [x] 2D grid rendering
- [x] Keyboard navigation with repeat
- [x] Mouse hover tooltips
- [x] Click-to-enter portals
- [x] Player position tracking
- [x] Portal metadata display

**Phase 2.5: Live Scene**
- [x] LiveScene wrapper skeleton
- [x] ESC back navigation
- [x] Portal metadata passing

### 🚧 In Progress

**Phase 3: SCADA Integration**
- [ ] Refactor pygame_scada_v2 into controller class
- [ ] Integrate SCADA rendering into LiveScene
- [ ] Add knee awareness with hysteresis
- [ ] Enhanced status line with E_th/E_pw

**Phase 4: Touch Input**
- [ ] TouchHandler class
- [ ] FINGERDOWN/MOTION/UP events
- [ ] Tap vs long-press detection

**Phase 5: Replay Scene**
- [ ] CSV file browser
- [ ] Scrubber with play/pause
- [ ] Speed control (0.5x-5x)
- [ ] Timeline visualization

**Phase 6: Performance**
- [ ] Text surface cache
- [ ] Dirty rect updates
- [ ] Panel versioning

**Phase 7: Optional**
- [ ] UDP sidecar daemon
- [ ] Start menu
- [ ] Fade transitions

## Usage

### Launch Grid World

```bash
cd lab
python main_scada_game.py
# or
RUN_SCADA_GAME.bat
```

### Navigate

1. Use Arrow/WASD to move green player cell
2. Hover over colored portals to see info
3. Click or press Space to enter portal
4. ESC to go back

### Portal Behavior

- **GPU/CPU Portals**: Should open LiveScene with device monitoring
- **Replay Portals**: Should open ReplayScene with file browser
- Currently displays placeholder until SCADA integration

## Next Steps

**Immediate Priorities:**

1. **Refactor SCADA Controller**: Extract pygame_scada_v2 rendering logic into `SCADAController` class that LiveScene can instantiate
2. **Complete Touch Support**: Add TouchHandler to GridScene for mobile devices
3. **Build ReplayScene**: CSV file picker with timeline scrubber
4. **Performance Polish**: Text cache, dirty rects, render versioning

**Future Enhancements:**

- UDP sidecar for snappier updates
- Start menu with settings
- Fade transitions between scenes
- 3D visualization option

## Design Principles

**Separation of Concerns:**
- Scene: UI navigation and interaction
- Controller: Data processing and rendering
- Manager: State and transitions

**Incremental Build:**
- Each phase is testable independently
- No breaking changes to existing v2 dashboard
- Backward compatible: v2 still works standalone

**Performance First:**
- Cached surfaces to avoid GPU allocations
- Versioned redraws to skip unchanged panels
- Dirty rects for minimal screen updates

**Input Agnostic:**
- Keyboard, mouse, touch all supported
- Each method has appropriate delay/timing
- Consistent behavior across devices

## Testing Checklist

- [ ] Grid world renders correctly
- [ ] Keyboard navigation smooth
- [ ] Mouse hover tooltip appears
- [ ] Click enters portal
- [ ] ESC pops scene stack
- [ ] Player cell visible and moves correctly
- [ ] Portal colors match config
- [ ] No crashes on invalid coordinates

## Known Limitations

1. **LiveScene**: Currently placeholder; needs SCADA integration
2. **ReplayScene**: Not yet implemented
3. **Touch**: Not yet implemented
4. **Performance**: No text cache or dirty rects yet
5. **Transitions**: No fade effects yet

## Success Metrics

**Phase 1-2 Goals** ✅
- Scene system functional
- Grid world navigable
- Multiple input methods work
- Clean architecture for expansion

**Remaining Goals**
- Full SCADA rendering in scene context
- Replay mode operational
- Touch input functional
- Performance optimized
- All test cases passing

## Notes

This foundation demonstrates game-like UX patterns for monitoring interfaces. The grid world makes system selection intuitive, and the scene manager enables smooth navigation between monitoring, replay, and configuration views.

The architecture supports future expansion: VR/AR overlays, 3D visualizations, and web mirroring can all plug into the same scene/data pipeline.

