# 버전별 확인 결과와 근거

원본 ADB 확인일: 2026-10-28. 후속 Android 12.1 R3의 60분·61회 검사, 재부팅 2회 및 Google·DRM 결과는 [최신 검증 기록](runtime-validation.md)을 참고합니다. 아래는 SKB 원본 Android 9/12의 ADB 메뉴 분석 이력입니다.

## Android 9: 실제 기기 확인

사용자가 BFX-AT100에서 `재생/일시정지 → 1 → 2 → 3 → 8 → 확인`으로 메뉴를 열었습니다. 해당 버전에서는 추가 비밀번호 없이 ADB를 활성화했고, PC가 연결을 요청한 뒤 TV에서 디버깅 허용을 승인했습니다.

인증된 ADB 연결로 읽은 값:

| 항목 | 결과 |
| --- | --- |
| 모델 | BFX-AT100 |
| Android / API | 9 / 28 |
| 빌드 | `PI.15.520.8-20200731 release-keys` |
| `sys.boot_completed` | `1` |
| `service.adb.tcp.port` | `5555` |
| `adb_enabled` | `1` |
| `development_settings_enabled` | `1` |
| `ro.adb.secure` | `1` |
| `ro.debuggable` | `0` |
| `persist.sys.skb.adb.disable` | 빈 값(미설정) |
| ADB 연결 상태 | `device` |
| 셸 권한 | `uid=2000(shell)` |

기기에 설치된 홈 앱과 설정 앱을 PC로 복사한 뒤 기기 원본과 PC 사본의 SHA-256 일치를 확인했습니다.

| 파일 | 바이트 수 | SHA-256 |
| --- | ---: | --- |
| Home.apk | 140,094,466 | `a51fb5dec0cd8cd9b90dcd5e19c8a914898c593e3b4d6628fb991ac11073cc18` |
| TvSettings.apk | 4,303,258 | `c4b0251252eded16846c4f44814970f0690cc2dbe907926d041954d912a9abf6` |

현재 홈 앱의 `com.skb.google.tv.main.HiddenMenuManager`에는 `HIDDEN_ANDROID_SETTING` 조합과 `android.settings.SETTINGS` 실행 경로가 있습니다. 이 버전의 키 입력 버퍼 초기화 시간은 1,000ms입니다. 허용 화면 조건도 함께 존재합니다.

실제 ADB 활성화는 사용자 조작과 연결 결과로 확인했습니다. 재부팅 후 ADB 설정 유지 여부는 이번 기록에서 별도로 검증하지 않았습니다.

## Android 12: 별도 순정 실기 확인

2026-10-31, 기존 Android 9 출발 기기와 별도인 순정 BFX-AT100에서 인증된 ADB를 확인했습니다. 사용자는 추가 메뉴 PIN을 입력하지 않아도 ADB를 켤 수 있었다고 확인했고, PC 최초 연결의 `unauthorized` 상태가 사용자 승인 후 `device`로 바뀌었습니다. 필요한 확인/OK 입력에는 페어링한 네트워크 리모컨을 사용했습니다.

| 항목 | 결과 |
| --- | --- |
| Android / API | 12 / 31 |
| 빌드 | `15.551.50-20250805`, `user/release-keys` |
| 보안 패치 | 2025-06-01 |
| 커널 | `4.9.269-abk000c-551r50-20250805` |
| vendor SDK / VNDK | 31 / 31 |
| 동적 파티션 선언 | `ro.boot.dynamic_partitions=true` |
| 인증된 TCP ADB | 5555 |

이 실측은 다음의 다른 업데이트 코드에 PIN 단계가 있다는 분석을 부정하지 않습니다. Android 12 안에서도 빌드·설정 경로를 구분합니다. 새 실기에는 기존 Android 9 정적 파티션 설치 절차를 적용하지 않았습니다. 계정·DRM 키·기기별 인증 자료는 비교·공개 대상에서 제외합니다.

## Android 12: 업데이트 파일 분석

분석 대상은 BFX-AT100용 `15.561.128-20260611`, Android 12 / API 31 업데이트입니다.

| 대상 | SHA-256 |
| --- | --- |
| 원본 update.zip | `40c39d3a522bd4a4416120c69e36ede5bd0b2954a17efcd15b465f88e10f6a20` |
| 포함된 TvSettings.apk | `a0809d1280325da87cbeac69c2a98dd54ac21ed26cf9f34cb1a317fce5cb9d36` |

`com.android.tv.settings.system.development.DevelopmentFragment`의 관련 경로를 확인했습니다.

1. `onPreferenceTreeClick()`에서 ADB 스위치를 켤 때 `showPasswordDialog()`를 호출합니다. 별도의 차단 정책이 켜져 있으면 스위치를 비활성화합니다.
2. `showPasswordDialog()`는 `pin_1`부터 `pin_6`까지 여섯 입력 칸을 사용하고 입력을 합칩니다.
3. `checkPassword()`는 다음 비교식으로 입력을 검사합니다.

```java
"0923".equals(value.substring(2))
```

여섯 자리 숫자 입력에서 앞 두 자리를 제외한 부분이 `0923`이면 조건을 만족합니다. 사용자가 알려준 **`000923`**은 이 조건에 맞으며, 앞 두 숫자는 다른 값이어도 이 비교 결과가 같습니다.

4. 검사 성공 경로는 `Settings.Global.adb_enabled=1`을 설정합니다.
5. `getDisableAdbStatus()`는 `persist.sys.skb.adb.disable`을 읽습니다. 해당 정책이 켜져 있으면 비밀번호 입력과 별도로 제한될 수 있습니다.

설정 앱의 코드 분석은 JADX 1.5.6으로 수행했습니다. 위 근거는 분석한 배포 파일의 동작 조건이며 Android 12가 설치된 실물에서 비밀번호를 입력한 결과는 아닙니다. 다른 모델이나 다른 배포 버전까지 같은 번호로 일반화하지 않습니다.
