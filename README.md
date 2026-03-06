# NAS-Streamliner

NAS-Streamliner는 영상 원본이 `Inbound` 폴더에 들어오면 파일 안정성을 확인한 뒤, `ffprobe` 메타데이터를 읽어 날짜/카메라별 구조로 정리하는 자동화 파이프라인입니다.

현재 포함 범위:

- `watcher.py`: `Inbound` 폴더 polling, 안정 파일 판정, 분류 작업 트리거
- `classifier.py`: `ffprobe` 기반 메타데이터 추출, 카메라 매핑, 표준 파일명 생성, `Storage/YYYY-MM-DD/CAM/Original` 이동
- `Quarantine`: 메타데이터 누락 또는 probe 실패 파일 격리
- `Manifest`: 처리 이력 JSONL 저장
- `SQLite State`: 워처 관찰 상태 저장

## 디렉터리 구조

```text
NAS-Streamliner/
├─ classifier.py
├─ watcher.py
├─ config/
│  ├─ settings.yaml
│  └─ cam_map.yaml
├─ docs/
│  └─ architecture.md
├─ runtime/
│  ├─ inbound/
│  ├─ logs/
│  ├─ quarantine/
│  ├─ state/
│  └─ storage/
├─ src/
│  └─ nas_streamliner/
│     ├─ camera_map.py
│     ├─ config.py
│     ├─ ffprobe.py
│     ├─ filesystem.py
│     ├─ logging_setup.py
│     ├─ manifest.py
│     ├─ models.py
│     ├─ naming.py
│     ├─ state_store.py
│     └─ services/
│        ├─ classifier.py
│        └─ watcher.py
└─ tests/
   ├─ test_camera_map.py
   └─ test_naming.py
```

## 파일명 규칙

원본 파일은 아래 규칙으로 표준화됩니다.

```text
YYYYMMDD_HHMMSS_<CAMERA_ALIAS>_<SANITIZED_SOURCE_STEM>.<ext>
```

예시:

```text
20260306_184512_A-CAM_FX3_C0012.mp4
20260306_184512_A-CAM_FX3_C0012__v02.mp4
```

분류 경로 예시:

```text
runtime/storage/2026-03-06/A-CAM/Original/20260306_184512_A-CAM_FX3_C0012.mp4
```

## 실행

```powershell
python -m pip install -e .
python watcher.py --config config/settings.yaml
python watcher.py --config config/settings.yaml --once
python classifier.py .\runtime\inbound\sample.mp4 --config config/settings.yaml
```

`ffprobe`는 시스템 PATH에 있어야 합니다.

