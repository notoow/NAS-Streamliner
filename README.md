# NAS-Streamliner

NAS-Streamliner는 영상 원본이 `Inbound` 폴더에 들어오면 파일 안정성을 확인한 뒤, `ffprobe` 메타데이터를 읽어 날짜/카메라별 구조로 정리하는 자동화 파이프라인입니다.

현재 포함 범위:

- `watcher.py`: `Inbound` 폴더 polling, 안정 파일 판정, 분류 작업 트리거
- `classifier.py`: `ffprobe` 기반 메타데이터 추출, 카메라 매핑, 표준 파일명 생성, `Storage/YYYY-MM-DD/CAM/Original` 이동
- `encoder.py`: `Original` 원본에서 `Proxy` 프록시 생성
- `process_media.py`: 수동 단건 처리용 classify + proxy encode 파이프라인
- `Quarantine`: 메타데이터 누락 또는 probe 실패 파일 격리
- `Manifest`: 처리 이력 JSONL 저장
- `SQLite State`: 워처 관찰 상태 저장
- `Preflight`: NAS 경로 존재 여부 및 쓰기 가능 여부 확인

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
│        ├─ encoder.py
│        └─ watcher.py
└─ tests/
   ├─ test_config.py
   ├─ test_camera_map.py
   ├─ test_encoder.py
   └─ test_naming.py
```

## 파일명 규칙

원본 파일은 아래 규칙으로 표준화됩니다.

```text
YYYYMMDD_HHMMSS_<CAMERA_ALIAS>_<SANITIZED_SOURCE_STEM>.<ext>
```

예시:

```text
20260306_184512_FX3-001_FX3_C0012.mp4
20260306_184512_FX3-001_FX3_C0012__v02.mp4
```

분류 경로 예시:

```text
runtime/storage/2026-03-06/FX3-001/Original/20260306_184512_FX3-001_FX3_C0012.mp4
runtime/storage/2026-03-06/FX3-001/Proxy/20260306_184512_FX3-001_FX3_C0012__proxy_720p_cfr.mp4
```

## 실행

```powershell
python -m pip install -e .
python watcher.py --config config/settings.yaml --validate-only
python watcher.py --config config/settings.yaml
python watcher.py --config config/settings.yaml --once
python classifier.py .\runtime\inbound\sample.mp4 --config config/settings.yaml
python encoder.py .\runtime\storage\2026-03-06\A-CAM\Original\sample.mp4 --config config/settings.yaml
python process_media.py .\runtime\inbound\sample.mp4 --config config/settings.yaml
```

`ffprobe`는 시스템 PATH에 있어야 합니다.

## NAS 경로 연결

기본 `config/settings.yaml`은 환경변수로 경로를 덮어쓸 수 있게 되어 있습니다.

PowerShell 예시:

```powershell
$env:NAS_STREAMLINER_INBOUND_ROOT = '\\172.30.1.210\video_ingest\Inbound'
$env:NAS_STREAMLINER_STORAGE_ROOT = '\\172.30.1.210\video_archive\Storage'
$env:NAS_STREAMLINER_QUARANTINE_ROOT = '\\172.30.1.210\video_archive\Quarantine'
python watcher.py --config config/settings.yaml --validate-only
python watcher.py --config config/settings.yaml
```

매핑 드라이브를 쓰는 경우에도 동일하게 경로만 바꾸면 됩니다.

```powershell
$env:NAS_STREAMLINER_STORAGE_ROOT = 'Z:\Video\Storage'
```

고정 설정 파일이 필요하면 [settings.synology.example.yaml](./config/settings.synology.example.yaml)을 복사해서 사용하면 됩니다.
