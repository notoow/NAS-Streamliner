# NAS-Streamliner Architecture

## 1. 운영 기준

- 워처와 분류기는 동일한 호스트에서 실행한다.
- 모든 경로 설정의 진입점은 `config/settings.yaml`이다.
- `cam_map.yaml` 경로도 `settings.yaml` 안에서 참조한다.
- 워처는 이벤트 기반이 아니라 polling 기반으로 동작한다.
- 파일은 "최소 2회 연속 동일 크기/mtime 관찰" + "최소 age 경과" 조건을 만족할 때만 처리한다.

## 2. 런타임 폴더

```text
runtime/
├─ inbound/        # 업로드 진입 폴더
├─ storage/        # 최종 보관 경로
├─ quarantine/     # 실패/미확정 파일 격리
├─ logs/           # 애플리케이션 로그
└─ state/          # sqlite 상태, manifest
```

## 3. 저장 경로 규칙

최종 원본 저장 경로:

```text
Storage/YYYY-MM-DD/<CameraAlias>/Original/<StandardizedFileName>
```

예시:

```text
runtime/storage/2026-03-06/A-CAM/Original/20260306_184512_A-CAM_FX3_C0012.mp4
```

격리 경로:

```text
Quarantine/YYYY-MM-DD/<reason>/<filename>
```

예시:

```text
runtime/quarantine/2026-03-06/ffprobe-failed/20260306_184700_ffprobe-failed_clip-001.mov
```

## 4. 파일명 정책

원본 표준 파일명:

```text
{capture_date_compact}_{capture_time_compact}_{camera_alias}_{source_stem}{ext}
```

필드 정의:

- `capture_date_compact`: `YYYYMMDD`
- `capture_time_compact`: `HHMMSS`
- `camera_alias`: `cam_map.yaml`에서 해석된 별칭, 예: `A-CAM`
- `source_stem`: 원본 파일명 stem을 경로 안전 문자로 정규화한 값

중복 처리:

```text
__v02, __v03, ...
```

## 5. 카메라 매핑 우선순위

1. `serials` 정확 매칭
2. `models` 정확 매칭
3. 설정의 `unknown_camera_alias`

같은 모델 바디가 여러 대라면 반드시 시리얼을 넣어야 한다.

## 6. 날짜 결정 우선순위

1. `ffprobe` 메타데이터의 `creation_time`
2. Apple QuickTime 계열 creation date 태그
3. `settings.yaml`이 허용하면 파일 수정 시간(`mtime`)
4. 위 모두 실패 시 `unknown_date_folder` 또는 Quarantine

시간대는 `classification.timezone` 기준으로 정규화한다.

## 7. 장애 처리

- `ffprobe` 실패: `ffprobe-failed` 사유로 Quarantine
- 날짜 미확정: 설정에 따라 Quarantine 또는 `unknown_date_folder`
- 카메라 미확정: 설정에 따라 Quarantine 또는 `unknown_camera_alias`
- 이동 실패: 예외 로그 남기고 state를 `failed`로 남긴다

## 8. 상태 저장

`runtime/state/nas_streamliner.db`

저장 항목:

- source path
- file size
- file mtime
- first seen / last seen
- stable since
- processing status
- destination path
- notes

이 구조 덕분에 재시작 이후에도 안정 판정과 중복 처리가 이어진다.

## 9. 모듈 책임

- `watcher.py`: CLI 진입점
- `classifier.py`: 단일 파일 수동 분류 CLI
- `src/nas_streamliner/services/watcher.py`: polling 스캔, 안정 파일 판정, 분류 호출
- `src/nas_streamliner/services/classifier.py`: probe, camera resolution, naming, safe move, manifest 기록
- `src/nas_streamliner/state_store.py`: SQLite 상태 저장소
- `src/nas_streamliner/ffprobe.py`: 메타데이터 추출
- `src/nas_streamliner/naming.py`: 파일명 및 중복 suffix 정책
- `src/nas_streamliner/filesystem.py`: 원자적 rename 우선, 불가 시 copy-verify-replace

