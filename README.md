# 바닷속 숨바꼭질 — 게임 에셋 팩

언리얼 엔진용 **비대칭 숨바꼭질 게임**(Dead by Daylight 참고)의 3D 에셋 모음입니다.
고장 난 잠수함을 고칠 부품을 모아 탈출하는 다이버(플레이어)와, 그들을 쫓는 심해 괴물(술래)이 등장합니다.

- 제작 도구: **Blender 5.3** (모델은 대부분 Python 스크립트로 생성 → 다시 만들기 쉬움)
- 대상 엔진: **Unreal Engine** (FBX, 단위 cm, 앞 방향 +X)
- 마지막 정리: 2026-11-18

> 📘 **언리얼에서 쓰는 방법(임포트 설정, 소켓, 재질, 콜리전, 블루프린트 구성)은 [`README_UNREAL.md`](README_UNREAL.md)** 에 자세히 있습니다.
> AI 에이전트는 그 문서 7장의 JSON을 기준 데이터로 쓰면 됩니다. 작업 이력은 [`WORK_LOG.md`](WORK_LOG.md).

---

## 무엇이 들어 있나

| 분류 | 에셋 | 비고 |
|---|---|---|
| **캐릭터** (뼈대·애니메이션) | 다이버 `SK_Diver`, 괴물 4종 `SK_Gigantura`(기간투라) · `SK_DeepSeaEel`(심해 뱀장어) · `SK_Kraken`(크라켄) · `SK_GiantIsopod`(거대 등각류) | 괴물은 4096 텍스처 구움. 다이버 애니메이션 9개, 괴물은 헤엄·대기·공격 |
| **다이버 장비** | 손전등, 산소통, BCD, 탱크 밴드, 마스크, 오리발, 레귤레이터 | 손전등 on/off 소켓 |
| **수리 부품** (수집 아이템) | 배터리, 밸브 파이프, 기어, 전선 릴, 퓨즈, 프로펠러 날, 선체 패치, CO2 스크러버 카트리지, 회로 기판, 모터 회전자, 방수액, 구리선, 용접기, 돔 유리 조각 6개 / 유리 가루 | 잠수함 수리 소켓에 그대로 붙음 |
| **잠수함 — 흰색 Mk2** (메인) | 외부 `SM_Sub2` 3종(게임 진행용 / 망가진 / 수리된) + **전용 선실** `SM_Sub2_Interior` 3종 + 사물함 문·전원 레버 | 수리 지점 8곳, 숨는 사물함 |
| **잠수함 — 기존 노란색** | `SM_Submarine` 3종 + 녹슨 버전, 선실 3종, 움직이는 부품 4개 | 예비·소품용 |
| **맵 소품** (숨는 장소) | 아래 표 | 모두 낡은 질감을 텍스처로 구움 |

### 맵 소품 — 숨는 장소

| 소품 | 숨는 방법 | 크기 | 텍스처 |
|---|---|---|---|
| **난파선** `SM_Shipwreck` | 화물칸(해치·선체 구멍), 조타실, 선원실 사물함 — 계단·문으로 서로 연결 | 24m 트롤 어선 | 4096 |
| **해저 동굴** `SM_SeaCave` | 큰 방의 벽감, 바위 뒤 — 출구 2개 | 19 × 13 × 6m 바위 언덕 | 4096 |
| **방파제** `SM_Breakwater` | 테트라포드 틈 3곳, 벽을 관통하는 배수관, 무너진 틈 | 30m 구간 | 4096 |
| **고래 뼈대** `SM_WhaleSkeleton` | 부러진 갈비뼈 틈으로 흉곽 안 | 약 24m | 4096 |
| **브라인 호수** `SM_BrinePool` (+ 수면 `SM_BrinePool_Surface`) | 소금물 속에 가라앉기 | 호수 7 × 4.6m | 4096 (수면은 반투명, 굽지 않음) |
| **테트라포드** `SM_Tetrapod` | — (직접 배치·흩뿌리기용 단독 소품) | 약 2.2m | 2048 |
| 해저 가로등 `SM_StreetLamp` | — | 3.4m | — |

---

## 폴더 구조

```
README.md               ← 이 문서 (전체 안내)
README_UNREAL.md        ← 언리얼 사용 가이드 (에셋별 크기·소켓·재질·콜리전 + AI용 JSON)
WORK_LOG.md             ← 작업 기록 (전체), 2026-11-09.md / 2026-11-16.md ← 날짜별 기록
SM_*.fbx                ← 정적 메시 (언리얼로 가져올 파일, 모델 1개 = 파일 1개)
SK_*.fbx                ← 캐릭터 (뼈대·애니메이션 포함)
Textures/               ← 구운 텍스처 T_<이름>_BaseColor / Normal / Roughness (/ Emissive)
Source/
├── DiveGear_Scene.blend     ← 모든 모델이 들어 있는 작업 씬
├── <모델명>.blend            ← 모델별 원본 (원점 기준, 실제 크기)
└── _tools/                  ← 모델을 만드는 Python 스크립트
```

---

## 언리얼로 가져오기 (요약)

1. FBX를 임포트합니다. **Import Uniform Scale = 1.0**, **Convert Scene = 켜기**, **Force Front XAxis = 끄기**.
2. 캐릭터(`SK_*`)는 Skeletal Mesh로, 나머지는 Static Mesh로 가져옵니다.
3. 구운 텍스처는 FBX에 경로가 들어 있어 자동으로 연결될 수 있습니다. 안 되면 `Textures/`의 BaseColor(sRGB) / Roughness(sRGB 끄기) / Normal(Normalmap)을 직접 연결하세요.
4. 상호작용 위치(숨기, 들어가기, 수리, 경첩 등)는 **`SOCKET_` 소켓**으로 들어 있습니다. 좌표 대신 소켓 이름으로 붙이면 됩니다.
5. 맵 소품은 삼각형이 많으니(약 5~17만) **Nanite**를 권장합니다. 숨는 장소는 **Use Complex Collision As Simple**.

자세한 내용과 에셋별 소켓 표는 [`README_UNREAL.md`](README_UNREAL.md)를 보세요.

---

## 모델 다시 만들기 / 수정하기

**FBX를 직접 고치지 말고**, `Source/_tools`의 스크립트나 `Source/*.blend`를 고친 뒤 다시 내보내세요.

맵 소품은 Blender를 화면 없이 실행해서 다시 만들고 텍스처를 굽습니다. 실행 순서는 다음과 같습니다.

```
mk.py  →  weather_bake.py  →  build_<소품>.py  →  export_all()
```

| 스크립트 | 만드는 것 |
|---|---|
| `mk.py` | 공용 모델링·FBX 내보내기 도구 (`export_unreal`) |
| `weather_bake.py` | 녹·때·이끼 절차적 재질(`weather`) + 텍스처 굽기·내보내기(`bake_export`) |
| `build_shipwreck.py` / `build_cave.py` / `build_breakwater.py` / `build_whale_skeleton.py` / `build_brine.py` / `build_tetrapod.py` | 각 맵 소품 |
| `build_sub2.py` / `build_sub2_interior.py` | 흰색 Mk2 잠수함 / 전용 선실 |
| `build_sub_variants.py`, `build_interior_detail.py`, `build_repair_parts2.py`, `build_parts3.py`, `build_dome_shards.py` | 기존 잠수함 버전·선실 디테일·부품 |
| `rig.py`, `horror.py`, `horror2.py`, `build_*` (괴물·다이버), `monsters_v2_pipeline.py`, `bake_textures.py` | 캐릭터 제작·리깅·텍스처 굽기 |
| `split_models.py` | 작업 씬에서 모델별 `.blend` 분리 |

- `mk.py`의 출력 경로 기본값은 `~/Documents/UnderwaterHideSeek_Assets`입니다. 다른 위치에서 쓰면 실행 후 `OUT_DIR` / `SRC_DIR`을 이 폴더로 바꿔 주세요.
- 소품마다 크기·배치 값(예: 난파선 기울기 `LIST`, 방파제 `CULVERT` 위치, 테트라포드 다리 길이 `L`)이 스크립트 위쪽에 있습니다.
- 새 에셋을 추가하면 `README_UNREAL.md`의 표와 7장 JSON, `WORK_LOG.md`를 같이 업데이트하세요.

### Blender에서 볼 때

- 작업 씬의 맵 소품은 굽기 전 원본 재질입니다. **뷰포트 셰이딩을 Material Preview**로 두면 구운 결과와 같은 모습이 보입니다.
- Intel 그래픽에서 화면이 깨지거나 꺼지면 Preferences → System → **GPU Backend = OpenGL**로 바꾸세요.

---

## 진행 상황

**완료**
- 캐릭터 5종, 다이버 장비, 수리 부품 전체
- 흰색 Mk2 잠수함 3종 + 전용 선실 3종 (메인으로 결정)
- 맵 소품 6종 + 텍스처 굽기 (난파선, 해저 동굴, 방파제, 고래 뼈대, 브라인 호수, 테트라포드)

**남은 일**
- 언리얼 프로젝트 선택 후 블루프린트(숨기, 수리 상호작용, 잠수함 상태 교체)
- 망가진 Mk2 잠수함(외부·선실) 텍스처 굽기 — 진행용·수리된 잠수함은 언리얼 타일링 재질을 슬롯에 입히는 방식 권장
- 다이버의 다른 동작(사물함 숨기, 사다리, 피격 등), 괴물의 수색·피격 애니메이션
- 무거운 모델 LOD (Nanite를 쓰지 않을 경우)

---

## 저장소 메모

- 수동 백업 폴더(`Source/_backup_*`)와 Blender 자동 백업(`*.blend1`)은 저장소에서 제외했습니다(`.gitignore`). 버전 관리는 git 기록으로 합니다.
- `.blend` / FBX / PNG는 수정할 때마다 저장소가 커집니다. 수정이 잦아지면 **Git LFS** 사용을 고려하세요.
