# Android 12 자동 시간 복구

Android 9에서 PHH Android 12.1/API 32로 올린 BFX-AT100의 후속 수정입니다. 기존 r1 ZIP에 포함된 기능이 아닙니다. 순정 Android 12 기기는 별도 검증 대상입니다.

## 관측한 재발 원인

시간대 `Asia/Seoul`과 자동 시간 설정은 맞았지만, 재연결한 기기의 실제 날짜는 2022년이고 `network_time_update_service`의 NTP 캐시는 비어 있었습니다. 초기 동기화 실패 후 재시도 제한을 소진해 다음 시도가 약 24시간 뒤로 예약돼 있었습니다. 같은 시점에 셋톱의 인터넷·DNS·여러 NTP 서버 응답은 정상이었고, 기본 동기화를 다시 요청하자 현재 시각이 복원됐습니다. 초기 통신 실패 자체가 DNS·상위망 준비 중 어느 단계였는지는 당시 부팅 로그 없이 단정하지 않습니다.

Android 12 기본 구현은 NTP 캐시가 비었어도 정해진 재시도 횟수를 넘기면 정상 폴링 주기로 돌아갑니다. 비교한 [AOSP NetworkTimeUpdateService](https://android.googlesource.com/platform/frameworks/base/+/android-12.1.0_r27/services/core/java/com/android/server/NetworkTimeUpdateService.java)에도 이 분기가 있습니다. 리소스 전용 동적 RRO 후보는 일반 리소스 조회만 바뀌고 부팅 초기 시스템 서비스에는 반영되지 않아 제외했습니다.

## 적용 방식

`src/time-recovery/`는 소규모 system-signed APK 소스입니다. Android의 `NtpTrustedTime`으로 응답을 검증하고, 검증된 시간만 `TimeDetector.suggestNetworkTime()`에 전달합니다. PC 시각·HTTP Date·임의 날짜로 시계를 덮어쓰지 않습니다. Android의 자동 시간 선택 정책을 유지하며 수동 시간 설정을 덮어쓰지 않습니다.

- 부팅 완료와 자기 패키지 업데이트 후 복구 작업을 예약합니다.
- 기본 네트워크가 늦게 준비되거나 NTP가 실패해도 1분 뒤 재시도를 예약합니다. 실패 횟수가 늘어도 24시간 대기로 전환하지 않습니다.
- 성공 후에는 6시간 뒤 재검증합니다. 다음 예약은 Android JobScheduler가 보존합니다.
- 작업마다 네트워크 요청을 마치고 종료합니다. 상주 무한 루프·root 셸·임의 명령 실행 기능이 없습니다.
- 서로 다른 고정 작업 ID 두 개를 번갈아 사용해 실행 중인 자기 작업을 예약으로 취소하지 않습니다. 다른 system UID 작업의 ID와 충돌하면 해당 작업을 보존합니다.
- 진단 수신기는 `DUMP`, JobService는 `BIND_JOB_SERVICE` 권한으로 보호합니다. 저장값은 동기화 결과와 시각·재시도 상태이며 계정·비밀번호·SSID는 저장하지 않습니다.

시간이 틀리면 HTTPS 검증도 실패할 수 있어, 부팅 복구는 Android의 인터넷 검증 완료 표시를 전제하지 않습니다. 기본 연결이 생긴 상태에서 NTP부터 확인합니다. 인터넷이 실제로 없으면 정확한 현재 시각을 새로 얻을 수 없으며, 하드웨어 RTC의 전원 차단 중 유지 능력은 이 소프트웨어로 보장하지 않습니다. 예약 시간도 Android 전원 관리와 시스템 부하에 따라 지연될 수 있습니다.

## 빌드·설치

해당 ROM과 일치하는 platform signer를 사용합니다. 다른 제조사 순정 펌웨어에서 APK만 설치해 같은 권한을 얻는 방법이 아닙니다. 현재 가드는 `BFX-AT100`·API 32를 확인하며, 일치하지 않는 기기에서는 작업하지 않습니다.

```sh
python src/time-recovery/build.py \
  --sdk /local/sdk --java-home /local/jdk \
  --platform-key /local/private/platform.pk8 \
  --platform-cert /local/private/platform.x509.pem \
  --out /local/output/time-recovery

adb -s YOUR_DEVICE install -r /local/output/time-recovery/BfxTimeRecovery.apk
adb -s YOUR_DEVICE shell am broadcast \
  -a local.bfx.timerecovery.SYNC \
  -n local.bfx.timerecovery/.ControlReceiver
```

펌웨어 파티션을 기록하거나 UTC·NTP 서버 설정을 임의로 변경하는 설치 과정이 아닙니다. 빌드된 APK와 서명 입력, 개인 현장 이미지는 저장소에 포함하지 않습니다.

## 확인·복구

```sh
adb -s YOUR_DEVICE shell am broadcast \
  -a local.bfx.timerecovery.STATUS \
  -n local.bfx.timerecovery/.ControlReceiver
adb -s YOUR_DEVICE shell dumpsys time_detector
adb -s YOUR_DEVICE shell date
```

성공 상태는 `last_suggestion_submitted=true`, `consecutive_failures=0`과 실제 현재 시각을 함께 확인합니다. 네트워크 시간 제안이 접수됐다는 기록만으로 실제 시각 변경을 단정하지 않습니다. 재부팅 후 자동 동작과, 네트워크가 늦게 돌아온 뒤의 복구도 확인합니다.

되돌리려면 이 패키지만 제거합니다. Android 기본 시간 서비스와 기존 자동 시간·시간대 설정은 유지됩니다.

```sh
adb -s YOUR_DEVICE uninstall local.bfx.timerecovery
```

## 실기기 검증 상태

기본 동기화 재요청 뒤 실제 시각 복원을 확인했습니다. 최종 공개 소스에서 만든 versionCode 2 APK를 현장 기기에 설치해 확인했습니다.

| 시험 | 결과 |
| --- | --- |
| 초기 후보의 연속 NTP 실패 | 5회 연속 실패에서도 매번 60초 재시도 유지. 마지막 같은 부팅 복구 관측 전 사용자가 전원/LAN을 분리해 그 부분은 성공 처리하지 않음 |
| 최종 빌드의 실패→복구 | 응답하지 않는 테스트 서버로 실패 재현 후 원래 서버 복원. 추가 SYNC 요청·자동 시간 토글 없이 예약된 작업이 복구, 실패 횟수 0으로 복귀 |
| 최종 빌드 소프트웨어 재부팅 | 2회 모두 새 부팅 이후의 NTP 제안과 현재 시각 일치 확인. 이전 부팅의 저장된 성공 기록을 제외하고 판정 |
| 재부팅 후 시각 오차 | 측정값 약 -1.4초 / -2.3초, ADB 조회·초 단위 양자화가 포함된 값 |
| 사용자 전원 재연결 | 초기 후보에서 사용자 전원 재연결 후 별도 수동 동기화 없이 현재 시각 복구 확인 |
| 기본 설정 | 자동 시간 켜짐·Asia/Seoul 유지, 테스트 NTP 서버를 원래 값으로 복원 |

시험 과정에서 시스템 시계를 일부러 과거로 돌리거나 계정 데이터를 지우지 않았습니다. 최종 빌드의 완전 전원 차단·장시간 오프라인 RTC 유지는 별도 미검증입니다. 이 결과는 순정 Android 12 기기에 이 APK를 설치한 결과가 아닙니다.
