# 순정 리모컨·HDMI 음량·Netflix: 확인한 수정과 남은 제약

2026-10-31, **Android 9에서 PHH Android 12.1로 올린 BFX-AT100 한 대**에서 확인한 결과입니다. 기존 r1 ZIP에 포함된 기능이 아니며, 공개 소스의 새 빌드 결과를 실기기에 설치한 결과와도 구분합니다. Google 앱, OTT APK, 계정, DRM 자료, 개인화 system 이미지는 배포하지 않습니다.

## 결과를 먼저 구분하기

| 항목 | 확인한 결과 | 한계 |
|---|---|---|
| BMM-BA03 | 순정 ARM32 HID 드라이버로 홈·방향키·확인·뒤로·측면 B tv 음량, 실제 사용자 확인 | 정확한 원본 커널·모듈·ID에 한정 |
| 늦은 연결·재연결 | 부팅 약 4분 뒤 연결, 실제 Bluetooth 재연결 후 순정 드라이버 자동 복귀 | 모든 리모컨 지원을 뜻하지 않음 |
| 음량 | HDMI 최대 음량 고정과 CEC 전달을 해제한 뒤 표시창·실제 음량 조절 확인 | 앞면 TV용 IR 음량과 측면 B tv 음량은 다른 경로 |
| Netflix `-14` | 실제 앱 코드의 `NOT_WHITELISTED_FOR_O`; 배터리 예외 추가 뒤 두 번의 완전 앱 재실행에서 경고 없음 | DRM 인증 오류로 단정하지 않음 |
| Netflix 영상 | 레거시 SurfaceView 구성에서 실제 TV 영상·소리 확인 | **재부팅 후 검은 영상 재발을 관측해 영구 해결로 확정하지 않음** |
| Netflix 전체 화면 | 정상 재생 후 동적 화면 overlay·구성 갱신으로 영상·좌우 여백 제거와 앱 재실행 성공 확인 | 부팅 초기 정적 overlay로 바꾼 후보는 재부팅 후 실패해 제외 |
| 화질 | 당시 디코더 보고 1920×1080, 약 24fps; HDMI 1080p60 | 4K·HDR·Netflix 기기 인증은 검증하지 않음 |
| 쿠팡플레이·다른 OTT | 소유자가 정상 작동 보고 | 특정 타이틀·해상도·서비스 인증을 전부 검증한 것은 아님 |

Widevine L1 세션 생성은 앞서 확인했지만, **L1이라는 값은 Netflix 4K 인증을 대신하지 않습니다.** 요금제·콘텐츠·앱·재생 장치·TV·HDMI 경로도 조건을 충족해야 합니다. [Netflix 공식 화질 안내](https://help.netflix.com/en/node/13444)를 참고합니다.

## 추가 진단: 같은 이미지 복원도 해결을 보장하지 않음

뒤이은 시험에서 **이전에 실제 재생이 됐던 동일 system/vbmeta로 되돌려도 검은 영상이 재발**했습니다. 따라서 앞서 성공한 설정값·동적 overlay 순서만 고정하면 항상 해결된다고 판단하지 않습니다. 아래 수동 절차는 성공 관측 기록이며 확정된 영구 해결책이 아닙니다.

이때 읽은 커널 상태는 다음과 같았습니다.

```text
HEVC decoder: 1920 x 1080, video/audio PTS advancing
SurfaceFlinger video rectangle: 85 0 1834 984
/sys/class/video/axis: 0 0 4 1079
horizontal output width: 5 pixels
hscale phase step: 0x40000000
VPP_hsc_endp: 0x4
```

디코딩·UI 영역과 달리 실제 영상 출력 평면이 5픽셀 폭으로 축소된 구체적 오류를 관측했습니다. 기존 제조사 영상 제어 서비스를 통해 그 좌표 하나를 `0 0 1919 1079`로 복원했고 반복 읽기에서 정상 폭 유지까지 확인했습니다. **그러나 소유자가 실제 TV에서는 여전히 자막·소리만 나온다고 확인했습니다. 좌표 복원만으로 해결되지 않습니다.** 잘못된 좌표를 쓴 구성요소와 재발 방지 방법도 아직 특정하지 못했습니다.

후속 진단에서는 좌표·스케일러가 정상인 동안에도 `/sys/class/video/video_global_output=0`, `video_layer1_state=0`을 관측했습니다. 비교한 커널 소스는 출력 값이 0이면 영상 레이어를 끄며, 원본 HWC의 `LegacyVideoPlane::setMute(bool)`는 이 출력 값을 바꾸는 ioctl을 사용합니다. 제조사 서비스를 통한 일회성 `0→1` 시험에서는 실제 레이어 상태도 `0→1`로 바뀌었습니다. **이 출력 시험 뒤 실제 TV 영상 확인과 출력을 끈 호출 조건의 규명은 아직 진행 중**입니다. 앱 재실행·재부팅 뒤에도 유지되는 수정으로 배포하지 않습니다.

이 진단에서는 펌웨어·UI 해상도·DRM 설정을 추가로 바꾸지 않았습니다. 초기 직접 쓰기는 권한에서 거부됐고, 이후 모델·해상도·정확한 비정상 값만 검사하는 로컬 진단 도구로 제조사 서비스를 호출했습니다. 이 도구의 private ABI 의존 코드·바이너리를 일반 사용자용 자동 복구로 배포하지 않습니다. 5픽셀이라는 값만 보고 다른 모델이나 정상 화면의 좌표를 강제 덮어쓰지 않습니다.

## 1. 순정 BMM-BA03 드라이버 경로

기존 GATT 보정은 일부 표준 키를 임시 주입했습니다. 순정 모듈은 BMM-BA03의 `005d:0004`를 정적 지원 목록에 포함하지 않았습니다. 이 작업은 **기기에 이미 있는 원본 ARM32 모듈**에 해당 ID 하나를 등록하고, 확인된 키배치를 선택합니다. ARM64 Android 12 모듈로 교체하거나 NUGU 서비스를 복원하지 않습니다.

예전 helper는 60초 후 종료됐습니다. 나중에 깨어난 리모컨이 일반 HID에 연결되면 순정 드라이버 전환이 빠져 확인·음량 등이 다시 누락됐습니다. 새 helper는 2초마다 해당 장치의 실제 드라이버를 확인합니다. 이미 순정 드라이버면 건드리지 않고, 거부된 장치는 일반 드라이버로 복원한 뒤 같은 열거 경로에 재시도하지 않습니다. 무선 연결이 없어도 종료하지 않으며 로그 크기는 제한합니다.

```sh
python src/stock-remote/build_overlay.py \
  --stock-hid /local/private/hid-skbrm.ko \
  --out /local/output/stock-remote-overlay
```

이 빌더는 원본 모듈 SHA-256을 검사하고 **프로젝트가 작성한 텍스트 파일만** 출력합니다. 모듈을 복사하거나 기기에 쓰지 않습니다. 가드 조건은 다음과 같습니다.

- 모델 `BFX-AT100`, 실제 `uname -r` 값 `4.9.113`, 커널 빌드 `#71 SMP PREEMPT`.
- 원본 `hid-skbrm.ko` SHA-256 `81972bf616a5f7ee798b5fce40019f46691f7bd21766b11c2a219fb23e243e1c`.
- 이미 로드된 `hid_skbrm`, 해당 `skbrm/new_id` 인터페이스, 단일 `005d:0004` 장치.
- 기존 PHH loader 도메인 `phhsu_daemon`. 다른 ROM에서 SELinux를 permissive로 바꾸어 통과시키지 않습니다.

`overlay-manifest.json`의 대상·권한·SELinux type에 따라 **오프라인 system 복사본**에 통합합니다. 기존 Google TV 리모컨 provider 설정도 보존합니다. [오프라인 통합·AVB·원본 보존 절차](connectivity.md#4-자신의-오프라인-system에-통합)를 따라 새 system/vbmeta를 검증합니다. 여기서는 flash 자동 설치기를 제공하지 않습니다.

공개 TV 설정 소스도 함께 갱신했습니다. `RemoteKeyService`는 실제 native 상태를 확인하면 GATT 주입을 닫고 종료합니다. 두 입력 경로를 동시에 유지하지 않습니다. [TV APK 빌드](connectivity.md#2-tv-설정-apk-빌드)의 기본 버전은 1021, 코드 rollback은 1022입니다.

첫 순정 드라이버 시험에는 UART 복구 경로를 유지합니다. 부팅 후 아래 상태와 실제 키를 함께 확인합니다.

```sh
adb -s YOUR_DEVICE shell getprop init.svc.bfx-stock-remote
adb -s YOUR_DEVICE shell getprop sys.bfx.stock_remote.state
adb -s YOUR_DEVICE shell dumpsys input
```

`running`과 `native-bound`, 해당 기기의 전용 keylayout, 홈·확인·뒤로·측면 B tv 음량의 **실제 동작**을 확인한 뒤에만 다음 부팅의 확인 marker를 만듭니다.

```sh
adb -s YOUR_DEVICE shell touch /data/local/tmp/bfx-stock-remote.confirm
```

거부하거나 복원할 경우에는 `bfx-stock-remote.disable` marker 후 재부팅합니다. 기존 GATT fallback은 부분 기능이므로 순정 음량 등 모든 키를 보장하지 않습니다. marker 제거·원본 system/vbmeta 복원 경로를 별도로 보존합니다. 다른 제품의 키배치를 이 ID로 바꾸지 않습니다.

## 2. HDMI 음량 표시·조절

실제 입력은 들어오는데 AudioService가 HDMI를 최대 음량 장치로 지정하고 CEC로 전달하면 셋톱 음량 표시와 값 변경이 생략될 수 있습니다. 이 기기는 framework API로 CEC 음량 전달을 끄고 HDMI를 `VARIABLE`로 지정해 복구했습니다. 설정은 재부팅 후에도 읽어 확인했고, 사용자가 표시창과 소리 변화를 확인했습니다.

새 공개 TV 설정에는 `android.permission.DUMP` 보유 호출자만 접근하는 좁은 receiver가 있습니다. 임의 root 명령이나 키 기록 receiver는 제공하지 않습니다. 자기 ROM의 platform 서명·privileged 권한이 일치하는 APK를 먼저 빌드·통합해야 합니다.

```sh
adb -s YOUR_DEVICE shell am broadcast \
  -n com.android.tv.settings/.bfx.HdmiVolumeReceiver \
  -a com.android.tv.settings.bfx.SET_CEC_VOLUME --ez enabled false
```

`enabled true`는 CEC 전달과 HDMI FULL 동작으로 돌립니다. 모든 TV에 일괄 적용할 권장 기본값이 아니며, **셋톱에서 음량을 조절하려는 구성**에만 선택합니다. AudioService의 `mFullVolumeDevices`, `mHdmiCecVolumeControlEnabled`, 실제 표시·소리를 각각 검증합니다.

## 3. Netflix 경고와 영상 출력은 별도 문제

이 기기의 공식 TV 앱 13.2.2 build 27249에서 `-14`는 `NOT_WHITELISTED_FOR_O`로 확인됐습니다. Android 배터리 예외로 추가한 뒤 완전 앱 재실행 두 번에서 경고가 사라졌고, 예외 값은 재부팅 후에도 유지됐습니다.

```sh
adb -s YOUR_DEVICE shell dumpsys deviceidle whitelist +com.netflix.ninja
adb -s YOUR_DEVICE shell dumpsys deviceidle whitelist
```

원래 예외가 없었던 기기에서 되돌리려면 `whitelist -com.netflix.ninja`를 사용합니다. 이 조치는 앱 설치·로그인·DRM 인증을 복원하는 것이 아닙니다.

검은 영상에는 Android 12의 SurfaceView 전달 경로 호환성을 시험했습니다. 실제 AOSP key는 `use_blast_adapter_sv`입니다.

```sh
adb -s YOUR_DEVICE shell settings get global use_blast_adapter_sv
# 위 원래 값을 먼저 기록한다.
adb -s YOUR_DEVICE shell settings put global use_blast_adapter_sv 0
adb -s YOUR_DEVICE shell am force-stop com.netflix.ninja
```

이는 **전역** 개발 설정으로 다른 SurfaceView 앱에도 영향을 줄 수 있습니다. 원래 `null`이면 `settings delete global use_blast_adapter_sv`, 원래 1이면 `settings put global use_blast_adapter_sv 1`로 복원합니다. 앱 데이터 삭제·로그아웃은 하지 않았습니다. 설정 0은 재부팅 후 유지됐어도 영상이 다시 검게 나오는 경우가 있었으므로, 이 값 하나만으로 영구 해결을 주장하지 않습니다.

영상 레이어의 종료 경고는 정상 재생 때도 관측돼 직접 원인으로 확정하지 않았습니다. 실제 TV에서 영상이 나오는지 확인해야 하며, 보호된 화면의 노트북 미러가 검다는 결과만으로 재생 실패를 판정하지 않습니다.

쿠팡플레이의 이전 거부에는 빈 `/data/su` 잔여 디렉터리와 custom GSI의 시험 서명 태그를 감지하는 조건이 각각 관측됐습니다. 현장에서는 빈 디렉터리임을 확인한 뒤 그 항목만 제거하고, custom/public-test-signed 상태를 명시하는 태그로 호환성 시험을 했습니다. 실제 서명 키·앱 검사 코드·DRM 키는 바뀌지 않았고 제조사 인증을 얻은 것이 아닙니다. 공개 vanilla r1에 이 현장 상태가 들어 있다는 의미가 아니며, 서비스가 custom 시스템을 허용한다고 보장하지 않습니다. 자기 기기의 내용을 확인하지 않고 경로를 재귀 삭제하거나 다른 기기 인증 자료를 복사하지 않습니다.

## 4. 전체 화면 수동 우회 절차 — 부팅 초기 정적 overlay와 구분

정상 상태에서는 앱 영역이 1920×984로 잡혀 영상 영역이 약 1749×984, 좌우 약 85픽셀 여백으로 표시됐습니다. 디코더가 보고한 원본은 1920×1080이었으므로 그 여백을 L3/SD 제한으로 해석하지 않습니다.

`src/tv-display-compat/`는 **동적 data RRO** 소스입니다. 부팅 초기 system의 Google TV remote provider overlay를 교체하지 않습니다. 실패했던 정적 zero-navigation 후보는 공개 안정 수정에서 제외했습니다.

```sh
python src/tv-display-compat/build_overlay.py \
  --sdk /local/sdk --java-home /local/jdk \
  --platform-key /local/private/platform.pk8 \
  --platform-cert /local/private/platform.x509.pem \
  --out /local/output/tv-display
```

자기 GSI의 platform 서명으로 빌드한 APK만 선택적으로 설치합니다. 원래 서명·overlay 정책이 다르면 적용을 중단합니다.

```sh
adb -s YOUR_DEVICE install -r /local/output/tv-display/BfxTvDisplayOverlay.apk
adb -s YOUR_DEVICE shell cmd overlay disable --user 0 local.bfx.tvdisplay.overlay
```

실제로 확인한 순서는 **기존 부팅 구성에서 먼저 같은 콘텐츠의 영상 재생을 확인 → 동적 overlay 활성화 → 구성 갱신 → 같은 콘텐츠 재생 → 앱 완전 종료·재실행**입니다. 영상이 처음부터 검다면 전체 화면 변경을 반복하지 않고 원래 구성으로 복원합니다.

```sh
adb -s YOUR_DEVICE shell wm size
adb -s YOUR_DEVICE shell wm density
# 관측 기기는 크기·밀도 override가 없는 1920x1080/320 상태였다.
adb -s YOUR_DEVICE shell cmd overlay enable --user 0 local.bfx.tvdisplay.overlay
# 해당 기본 상태에서만 잠깐 갱신하고 override를 남기지 않는다.
adb -s YOUR_DEVICE shell wm density 319
adb -s YOUR_DEVICE shell wm density reset
```

기존 override가 있는 다른 기기에는 `reset`을 그대로 적용하지 않습니다. 원래 값을 보존·복원해야 합니다. 위 절차는 **수동 우회**이며 재부팅 시 자동 실행하도록 넣지 않았습니다. 해상도 강제 720p·정적 navigation 변경·설정값 하나 복사로는 실패한 비교도 기록했습니다. 검은 영상이 재발하면 다음을 복원하고, 변경 전 system/vbmeta와 나란히 비교합니다.

```sh
adb -s YOUR_DEVICE shell cmd overlay disable --user 0 local.bfx.tvdisplay.overlay
```

프레임·DRM 키·HDCP·앱 인증 검사를 무력화하지 않습니다. 원래 화면비가 다른 콘텐츠의 정상 여백을 강제로 늘려 없애지도 않습니다.

## 다음 동일 모델·다른 Android 버전 시험

다음 대상도 해지 안내가 나오는 BFX-AT100이라는 사용자 설명을 받았지만, 현재 원본 버전·커널·파티션·AVB 구조는 아직 확인하지 않았습니다. **해지 안내만으로 Android 9 정적 파티션이라고 판단하지 않습니다.** 새 기기의 원본을 읽고 검증한 뒤 별도 결과를 기록할 예정이며, 현재 기기용 delta·env·misc·DRM 자료를 새 기기에 복사하지 않습니다.
