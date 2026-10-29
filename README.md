# BFX-AT100: Android 9에서 Android 12.1 기본 시스템으로 판올림

**당근에서 중고로 구매한 SK브로드밴드 BFX-AT100이 Android 9에 멈춰 있어, 기존 파티션을 유지하면서 Android 12.1 기반 AOSP/PHH GSI로 판올림한 개인 작업 기록과 보조 소스입니다.**

출발점은 Android 12 기기가 아닙니다. **Android 9 → Android 12 계열의 실제 OS 판올림**을 진행했습니다. 여기서 ‘기본 버전’은 B tv용 제조사 시스템 대신 사용한 **PHH v416 vanilla Android 12.1/API 32**를 뜻합니다. SKB 공식 Android 12 펌웨어를 성공적으로 설치한 결과나, 공식 Android TV 인증 제품 이미지를 배포하는 프로젝트가 아닙니다.

확인일: **2026-10-29**. 게임·에뮬레이터 설정은 이 저장소에 포함하지 않습니다.

**설치용 이미지:** [Releases에서 r1 ZIP 다운로드](https://github.com/a77ila2000/SKB-BFX-AT100-ADB/releases/tag/bfx12.1-vanilla-20261029-r1) · [다운로드·자기 기기 검증·UART 설치·첫 설정 안내](docs/distribution.md). 개인정보와 ADB 키를 넣지 않은 실험 배포본이며, 원본 덤프가 아닙니다. SKB의 OTA 업로드 메뉴에 넣는 ZIP도 아닙니다. 배포용 재빌드 자체의 실기기 부팅은 미시험이며, 현장 개인화 이미지의 부팅 검증과 구분합니다.

## 왜 이 작업을 했나

구매한 셋톱은 B tv 계약이 해지된 상태였고, 기존 화면에는 고객센터에 연락해 다시 이용하라는 해지 안내가 표시됐습니다. Android 9에 머물러 있는 이 기기에서 정상적인 B tv 서비스·업데이트 이용을 완료할 수 없어, 일반 Android 시스템으로 활용하는 방향을 택했습니다.

다만 **계약 해지 때문에 펌웨어 파일 자체가 전혀 다운로드되지 않았던 것은 아닙니다.** 실제 recovery에서는 동일 모델용 Android 12 업데이트의 다운로드와 전체 파일 서명 검증이 성공했습니다. 그 뒤 설치 약 24%에서 실패·재부팅이 반복됐고, UART로 확인한 직접 원인은 **구형 정적 파티션에서 `super` 동적 파티션으로의 전환 실패**였습니다. 해지 상태와 설치 실패의 기술적 원인을 구분해 기록합니다.

| 항목 | 출발 상태 | 실패한 공식 OTA의 대상 | 실제 적용 결과 |
|---|---|---|---|
| 시스템 | SKB Android 9 | SKB Android 12 | PHH vanilla Android 12.1 |
| API | 28 | 31 | 32 |
| 빌드/기반 | `PI.15.520.8-20200731` | `15.561.128-20260611` | PHH v416, `arm32_binder64-ab` |
| 파티션 | 개별 `system/vendor/product/odm` | `super` 안의 논리 파티션 요구 | 기존 정적 구조 유지 |
| 결과 | 해지 안내, 업데이트 반복 실패 | 동적 파티션 갱신 오류 25 | 실제 부팅·화면·유선 통신·PCM 소리 확인 |

## 공식 업데이트가 실패한 지점

```text
whole-file signature verified against RSA key 0
now upgrade from android 28 to S
upgrade from old android to new, need upgrade by two step.
else case, ota_zip_check() != 1
format: mke2fs failed (256) on /dev/block/by-name/metadata
DTB NOT changed...
open failed: /dev/block/by-name/super: No such file or directory
Failed to load dynamic partition metadata.
assert failed: update_dynamic_partitions(...)
error: 25
```

기존 recovery/파티션에서 새 구조로 옮기는 선행 단계가 이 시도에서 실행되지 않았습니다. ‘Android 9가 너무 오래돼서’라는 추측만으로 결론내린 것이 아니며, **특정 중간 버전을 반드시 설치해야 한다거나 Android 10·11을 차례로 거쳐야 한다는 절차는 확인하지 못했습니다.** 자세한 구분은 [공식 OTA 실패 분석](docs/ota-failure.md)을 참고하세요.

## 어떤 방식으로 Android 12를 올렸나

1. 원래 Android 9 기기의 eMMC와 파티션을 읽어 백업하고 별도 해시 검증을 했습니다.
2. 실제 32비트 userspace와 Binder 프로토콜을 확인해 PHH v416 **ARM32/Binder64 vanilla** 이미지를 선택했습니다.
3. 구형 kernel/vendor와 정적 파티션을 유지하고, 새 GSI의 `system`·`product`·`system_ext`가 올바르게 보이도록 fstab과 부팅 인자를 조정했습니다.
4. system 이미지와 그에 맞는 vbmeta를 만들고 AVB 서명·해시 트리·변경하지 않은 파티션 기술자를 검증한 뒤 적용했습니다.
5. 첫 부팅의 SystemUI·구형 앱 충돌, 고정 IP 저장 후 부팅 반복, 부팅 애니메이션과 오디오 HAL의 오류 경로를 조사하고 수정했습니다.
6. USB를 뺀 상태에서 전원을 완전히 분리·재연결하고 실제 TV 화면과 소리를 확인했습니다.

관측한 기기의 공개 AOSP 시험 키 수용 조건을 이용한 장치별 작업입니다. **AVB green은 이 수정 이미지의 검증 통과를 뜻하며 제조사 정식 펌웨어·잠금 해제 성공·일반 기기에 대한 범용 설치 보증을 뜻하지 않습니다.**

## 문서와 소스

- [설치 구조·작업 순서·복구 범위](docs/install.md)
- [배포 이미지로 설치하기: 검증부터 첫 부팅까지](docs/distribution.md)
- [공식 OTA의 24% 실패와 파티션 차이](docs/ota-failure.md)
- [호환성 수정 및 실제 검증 범위](docs/compatibility.md)
- [소스 사용법·공개 범위·개인정보 제외 기준](docs/source-and-privacy.md)
- [기존 SKB Android 9/12의 ADB 진입 안내](docs/adb-stock.md)
- [기존 ADB 분석 근거](docs/verification.md)

Git 저장소에는 **오프라인 이미지 구성·검증 도구 및 진단 보조 코드**를, Releases에는 **개인정보를 제거한 설치용 system/vbmeta ZIP**을 제공합니다. 기기의 flash를 자동으로 덮어쓰는 설치기는 제공하지 않습니다. 제조사 OTA 전체·원본 APK·eMMC 덤프·ADB 키·개인 정보는 배포하지 않습니다.

## 확인된 결과와 한계

- Android 12 계열/API 32 부팅 완료와 HDMI 화면, 인증된 ADB, DHCP 유선 통신을 확인했습니다.
- USB 없는 완전 전원 부팅, 실제 TV의 PCM HDMI 소리를 확인했습니다.
- 오래된 GPU/vendor의 모든 기능이나 장시간 안정성을 보증하지 않습니다.
- Google Play/어시스턴트는 현재 vanilla 구성에 정상 통합되지 않았고, DRM·OTT 인증/재생도 검증하지 않았습니다.
- 기존 Wi-Fi 추정은 정정했습니다. 확인한 무선 칩은 Bluetooth 전용이며 사용 가능한 Wi-Fi 인터페이스는 확인하지 못했습니다.
- 기반 보안 패치는 **2022-07-05**입니다. 설치 작업일과 시스템 보안 패치 날짜는 다릅니다.

## 기반 프로젝트

- [PHH AOSP 12.1 v416](https://github.com/phhusson/treble_experimentations/releases/tag/v416)
- [AOSP GSI](https://source.android.com/docs/core/tests/vts/gsi)
- [AOSP non-A/B 동적 파티션 OTA](https://source.android.com/docs/core/ota/dynamic_partitions/nonab)
- [AOSP Android Verified Boot](https://android.googlesource.com/platform/external/avb/+/refs/tags/android-12.0.0_r34/README.md)
