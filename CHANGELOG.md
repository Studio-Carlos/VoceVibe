# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2024-12-01

### Added
- **Prompt Rate Slider**: Adjustable generation interval from "Fastest" (phrase-driven) to 30s.
- **History Slider**: Adjustable context window from 5s to 60s.
- **Visual Memory**: Maintains continuity between prompts.
- **Strict String Output**: `BrainEngine` now outputs raw strings via OSC, removing all JSON.
- **OSC Connection Check**: Added `is_connected()` to prevent shutdown errors.
- **Session Logging**: Added `session.log` to `.gitignore`.

### Changed
- **System Prompt**: Updated to explicitly forbid JSON and enforce SDXL Turbo syntax.
- **UI**: Removed "Style | Mood" display for a cleaner interface.
- **STT Engine**: Migrated to PyTorch CPU (`kyutai/stt-1b-en_fr`) with deterministic decoding (`temp=0.0`).
- **Architecture**: Implemented producer-consumer pipeline for audio stability.

### Fixed
- **Crash**: Removed unsupported `repetition_penalty` argument from `LMGen`.
- **Shutdown**: Fixed "Not connected" errors during application stop.
- **Hallucinations**: Eliminated by using `temp=0.0` and strict token filtering.

## [1.0.0] - 2024-11-24

### Added
- Initial release of VoiceVibe.
- Real-time STT with Kyutai Moshi (MLX backend).
- Basic BrainEngine with Ollama integration.
- CustomTkinter UI with real-time dashboard.
