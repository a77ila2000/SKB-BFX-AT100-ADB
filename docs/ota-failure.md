# 공식 Android 12 OTA가 약 24%에서 실패한 이유

## 배경과 직접 원인 구분

당근에서 구매한 중고 BFX-AT100은 Android 9에 남아 있었으며, B tv 계약이 해지된 상태라는 안내 화면을 표시했습니다. 정상적인 가입 서비스 흐름을 이용할 수 없었던 것이 작업의 배경입니다. 그러나 recovery의 업데이트 파일 다운로드는 실제로 성공했으므로, 해지 상태만을 이유로 업데이트 서버가 모든 전송을 차단했다고 기술하지 않습니다.

공식 OTA의 출발 환경은 Android 9/API 28, `PI.15.520.8-20200731`; 도착 대상은 Android 12/API 31, `15.561.128-20260611`이었습니다. 파일의 모델 조건도 BFX-AT100으로 일치했습니다.

## 파일 손상과 서명 문제부터 배제

보존한 패키지는 828,288,036바이트였으며 ZIP CRC 검사와 패키지 인증서 기준 전체 파일 서명 검증을 통과했습니다. 더 중요하게는 **실제 기기의 recovery에서 전체 파일 서명 검증이 성공**했습니다. 다운로드 100%와 서명 성공 뒤 설치 24%에서 멈춘 이번 시도를 단순 다운로드 손상이나 서명 키 불일치로 설명하지 않습니다.

두 번째 네트워크 수집 사본은 완료되지 않아 전체 해시 동일성을 확인하지 못했습니다. 첫 완전 사본 확보와 여러 사본의 동일성 검증을 혼동하지 않습니다.

## 파티션 구조 차이

| 기존 Android 9 | Android 12 OTA의 기대 |
|---|---|
| 개별 system/vendor/product/odm 물리 파티션 | super 내부의 system/vendor/product/odm 논리 파티션 |
| system 크기 `0x5c800000` = 1,480MiB | 새 DT의 super 크기 `0x65200000` = 1,618MiB |
| `/dev/block/by-name/super` 없음 | `update_dynamic_partitions`에서 super 메타데이터 사용 |
| 구형 recovery 환경 | 새 파티션 구조를 처리할 선행 전환 필요 |

AOSP에서는 non-A/B 동적 파티션 OTA를 패키지 updater가 처리합니다. 따라서 기존 system 하나를 super로 이름만 바꾸거나 업데이트 파일을 다시 보내는 것으로 해결되지 않습니다. [AOSP 설명](https://source.android.com/docs/core/ota/dynamic_partitions/nonab)

## 실제 관측 순서

```text
whole-file signature verified against RSA key 0
now upgrade from android 28 to S
Cannot find legal dtb!
read dtb from /dev/dtb failed!
upgrade from old android to new, need upgrade by two step.
else case, ota_zip_check() != 1
run_program: execv failed: No such file or directory
format: mke2fs failed (256) on /dev/block/by-name/metadata
DTB NOT changed...
open failed: /dev/block/by-name/super: No such file or directory
Failed to load dynamic partition metadata.
script aborted: assert failed: update_dynamic_partitions(...)
error: 25
```

새 bootloader/DTB/recovery를 먼저 교체하는 스크립트 분기는 `ota_zip_check() == "1"`인 경우에만 실행되지만, 관측한 실행은 그 분기를 건너뛰었습니다. 분석한 바이너리의 해당 정상 반환 경로도 문자열 `"0"`으로 연결됐습니다. `mke2fs` 부재는 앞선 recovery 환경 불일치이고, 설치를 최종 중단한 조건은 **없는 super를 대상으로 한 동적 파티션 갱신 assert**입니다. 이후 recovery가 재부팅을 요청하면서 반복됐습니다.

## 확인하지 못한 부분

- DTB 파싱이 거부된 더 깊은 원인과 제조사의 정상 전환 절차 전체.
- 이 기기에서 안전하게 사용할 수 있는 특정 중간/서비스 패키지의 버전.
- Android 10과 11을 각각 설치해야 한다는 필수 조건.
- 같은 모델의 모든 다른 기기·최신 제조사 절차에서도 동일하게 실패한다는 일반화.

따라서 결론은 **‘이 Android 9 기기의 당시 구조와 확보한 공식 Android 12 OTA 조합으로는 정상 전환이 완료되지 않았다’**입니다. 이 때문에 기존 구조를 유지한 별도 Android 12.1 GSI 포팅으로 방향을 바꿨습니다. 가입 인증을 우회해 B tv 방송 서비스를 복원한 작업은 아닙니다.
