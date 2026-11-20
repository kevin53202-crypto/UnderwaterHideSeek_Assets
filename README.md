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
| **캐릭터** (뼈대·애니메이션) | 다이버 `SK_Diver`, 괴물 4종 `SK_Gigantura`(기간투라) · `SK_DeepSeaEel`(심해 뱀장어) · `SK_Kraken`(크라켄) · `SK_GiantIsopod`(거대 등각류) | 괴물은 4096 텍스처 구움. 다이버 애니메이션 15개(헤엄·도망·줍기·수리·끼우기·피격·사망·숨기), 괴물은 헤엄·대기·공격·수색·피격 |
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
    └── dev/                 ← 작업 보조 스크립트 (빌드·미리보기·FBX 검사·화면 열기)
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
- **애니메이션 확인**: `anim_picker.py`를 붙여 열면 3D 화면 오른쪽 사이드바(N 키)에 **"Anim" 탭**이 생기고, Model 목록에서 모델을 고른 뒤 `DV_Pickup` 같은 이름 버튼을 누르면 그 동작이 반복 재생됩니다(스페이스바 = 멈춤). 명령은 아래 "작업 보조 스크립트" 표 참고.
- 모델이 **분홍색**이면 텍스처를 못 찾은 것 → `fix_texture_paths.py` 실행.
- `open_view.py`로 열면 대상 모델만 보이는 로컬 뷰입니다. `/` 키로 전체 모델을 봅니다.

---

## 진행 상황

**완료**
- 캐릭터 5종, 다이버 장비, 수리 부품 전체
- 흰색 Mk2 잠수함 3종 + 전용 선실 3종 (메인으로 결정)
- 맵 소품 6종 + 텍스처 굽기 (난파선, 해저 동굴, 방파제, 고래 뼈대, 브라인 호수, 테트라포드)
- **2026-11-20**
  - **다이버 애니메이션 v3** (`build_diver_anims_v3.py`): 기존 9개 수정 + 새 6개 = 15개.
    - 고친 것: 팔이 일자로 뻗던 문제(손 IK 목표가 리그 위치 −3.5m를 무시한 버그), 꼿꼿이 선 떠 있기 → 수평 개구리 트림 자세, 줍기 중 몸이 뒤집히던 것, 수리 패널이 팔 길이보다 멀던 것.
    - 추가: `DV_SwimFast`(도망), `DV_Hit`(피격), `DV_Death`(사망), `DV_Hide_Enter` / `_Idle` / `_Exit`(웅크려 숨기).
  - **거대 등각류 v3** (`build_isopod_v3.py`): 실물 Bathynomus 형태(다리는 몸 아래, 겹친 판, 머리 옆 납작한 눈). 색은 갈색 계열로 재도색 완료.
  - 거대 등각류 **갈색 재도색**(회색·흰색 제거), 괴물 4종 **수색(`*_Search`)·피격(`*_Hit`)** 애니메이션 추가(`build_monster_anims_extra.py`).
  - **괴물 3종을 크라켄 수준으로 업그레이드**: 심해 뱀장어 v3(굵은 몸, 갈고리 가시, 푸른 발광점, 호박색 눈 9개, 뼈 16개로 매끄러운 동작), 기간투라 v4(크라켄 피부 색감, 새 대기·헤엄·물기), 거대 등각류 v4(돌기·따개비·흉터, 갈색만). 다시 굽기는 `dev/run_monster.py`.
  - 도구: `anim_picker.py`(버튼으로 애니메이션 보기), `fix_texture_paths.py`(분홍 텍스처 수정), `open_view.py` 로컬 뷰·전체 보기.

**남은 일**
- 언리얼 프로젝트 선택 후 블루프린트(숨기, 수리 상호작용, 잠수함 상태 교체)
- 망가진 Mk2 잠수함(외부·선실) 텍스처 굽기 — 진행용·수리된 잠수함은 언리얼 타일링 재질을 슬롯에 입히는 방식 권장
- 다이버의 다른 동작(사다리 등) — 다이버 피격·사망·숨기·도망, 괴물 수색·피격은 추가됨
- 무거운 모델 LOD (Nanite를 쓰지 않을 경우)

---

## 다음 작업자를 위한 안내 (사람 · AI 공통)

### 작업 시작하기

1. 이 README → [`WORK_LOG.md`](WORK_LOG.md)(4장 "남은 일") → [`README_UNREAL.md`](README_UNREAL.md) 순서로 읽습니다.
   Claude Code라면 새 대화에서 **"README와 WORK_LOG 읽고 다음 작업 진행해줘"** 로 시작하면 됩니다.
2. Blender: `C:\Program Files\Blender Foundation\Blender 5.3\blender.exe` (5.3 기준으로 작업, 5.2.3으로 만든 파일도 열림).
3. 아래 명령은 모두 **이 폴더(저장소 루트)에서** 실행합니다. `blender`는 위 실행 파일 경로입니다.

### 작업 보조 스크립트 (`Source/_tools/dev/`)

| 스크립트 | 하는 일 | 명령 |
|---|---|---|
| `run_prop.py` | 빌드 스크립트 실행(+ 텍스처 굽기·FBX 내보내기) 후 결과 씬을 **사본으로** 저장 | `blender -b --factory-startup Source/DiveGear_Scene.blend --python Source/_tools/dev/run_prop.py -- build_cave.py --export --save C:/temp/scene_new.blend` |
| `preview_render.py` | 빌드 직후 모양 확인용 렌더링(재질 단색) | `blender -b --factory-startup Source/DiveGear_Scene.blend --python Source/_tools/dev/preview_render.py -- build_cave.py C:/temp/shots shots.json` |
| `verify_fbx.py` | FBX를 빈 씬에 다시 불러와 재질·텍스처·삼각형·소켓 검사(+ 구운 텍스처로 렌더링) | `blender -b --factory-startup --python Source/_tools/dev/verify_fbx.py -- SM_SeaCave.fbx --render C:/temp/shots shots.json` |
| `open_view.py` | Blender 화면을 특정 모델만 보이게 열기(로컬 뷰, 뼈 숨김, Material Preview; `/`로 전체 보기). `-- ALL`이면 모든 모델 | `blender Source/DiveGear_Scene.blend --python Source/_tools/dev/open_view.py -- SeaCave 18 -14 12 0 0.5 1.5` |
| `run_monster.py` | 괴물 하나를 스크립트로 다시 만들고 수색·피격 동작 추가 → 4096 텍스처 굽기 → `SK_*.fbx` → 씬 **사본** 저장(미리보기 렌더도 가능) | `blender -b --factory-startup Source/DiveGear_Scene.blend --python Source/_tools/dev/run_monster.py -- . C:/temp build_eel_v3.py DeepSeaEel_Rig SK_DeepSeaEel_Body DeepSeaEel --export C:/temp/scene_new.blend` |
| `anim_picker.py` | 3D 화면 오른쪽 사이드바(N)에 **"Anim" 탭** 추가: Model 목록에서 모델을 고르면 화면이 그 모델로 이동하고, 동작 버튼을 누르면 반복 재생(메뉴 없이 동작 확인) | `blender Source/DiveGear_Scene.blend --python Source/_tools/dev/anim_picker.py --python Source/_tools/dev/open_view.py -- Diver_Rig 2.6 -2.8 1.6 0 -0.2 0.9` |
| `fix_texture_paths.py` | 찾을 수 없는 텍스처(다른 PC 절대경로 등)를 `Textures/`의 같은 이름 파일로 다시 연결(분홍색 해결). **씬을 교체한 뒤 꼭 실행** | `blender -b --factory-startup Source/DiveGear_Scene.blend --python Source/_tools/dev/fix_texture_paths.py` |

`shots.json` 예: `[{"name": "cave_34", "roots": ["SeaCave"], "cam": [18, -14, 12], "look": [0, 0.5, 1.5], "lens": 22}]` (좌표는 모델 기준점 기준, m)

### 새 맵 소품을 만들 때의 절차 (이번에 쓴 방식)

1. `Source/_tools/build_<이름>.py`를 기존 소품(예: `build_breakwater.py`)을 본떠 만듭니다. 구성: `mats()`(재질 + `weather()` 값) → `build()`(모델 + 소켓) → `export_all()`(굽기·내보내기).
2. `preview_render.py`로 여러 각도·내부를 렌더링해 **눈으로 확인 → 고치기**를 반복합니다. 숨는 장소는 **실제로 들어갈 수 있는지**(입구가 막히지 않았는지, 공간이 파였는지) 꼭 확인합니다.
3. `run_prop.py ... --export --save <사본>`으로 굽고 FBX를 내보낸 뒤, `verify_fbx.py`로 다시 불러와 검사합니다.
4. 모델별 `.blend` 분리: `blender -b --factory-startup --python Source/_tools/split_models.py -- <사본.blend> Source <RootName>`
5. 작업 씬 교체: **열려 있는 Blender 창 제목에 `*`(저장 안 된 변경)가 있으면 덮어쓰지 말고** 먼저 닫게 한 뒤, `Source/DiveGear_Scene.blend`를 사본으로 바꿉니다(필요하면 이전 파일을 따로 보관).
6. `README_UNREAL.md`(맵 소품 섹션 + 7장 JSON), 이 README의 표, `WORK_LOG.md`를 업데이트하고 커밋합니다. JSON은 파싱되는지 확인하세요.

### 알아 둘 함정 (이번 작업에서 실제로 겪은 것)

| 증상 | 원인 / 해결 |
|---|---|
| 불리언으로 판 공간 일부가 **조용히 안 파임** | 겹치는 잘라내기 모양을 순서대로 빼면 실패할 수 있음 → **하나의 오브젝트로 합친 뒤 한 번에** Difference, `use_self = True`, `use_hole_tolerant = True` (`build_cave.py`) |
| 회전시킨 부품이 엉뚱한 곳에 감 | `mk.py`의 `box()`/`cyl()`은 **위치로 옮긴 뒤 회전**함 → 회전이 있으면 `box(size, (0,0,0), T(위치) @ 회전)` 형태로 |
| 얇은 판이 예상과 반대쪽으로 두꺼워짐 | `bmesh.ops.solidify`는 **법선 반대쪽**으로 두께를 줌 |
| FBX 소켓 이름에 `__SC` 같은 꼬리가 붙음 | 씬에서는 이름이 겹치지 않게 꼬리를 붙여 두고, 각 스크립트의 `export_all()`이 내보낼 때 뗌 → 직접 `export_unreal`을 부르면 꼬리가 남음 |
| 구멍 둘레에 이상한 음영, 계단 모양 가장자리 | 격자 면을 통째로 빼면 계단이 생김 → 경계 정점을 매끈한 곡선 위로 옮김(`build_shipwreck.py`의 `hull_bm`), 음영은 녹슨 테두리 같은 덮개로 가림 |
| 면 단위 재질 경계가 픽셀처럼 보임 | 얼룩·상처는 면 재질 대신 **표면에 붙인 얇은 패치(decal)** 나 굽기용 절차적 재질(`weather()`)로 |
| 숨는 위치 소켓이 바닥 아래·벽 속에 생김 | 광선을 바위 속에서 쏘면 엉뚱한 면을 맞음 → 소켓 높이를 출력해서(`run_prop.py`가 보여 줌) 확인 |
| `mk.py`의 결과가 `~/Documents`로 저장됨 | 기본 경로 → `OUT_DIR`/`SRC_DIR`을 이 폴더로 바꿔서 실행(`run_prop.py`가 해 줌) |
| Blender 강제 종료 / 글씨·아이콘 깨짐 (Intel 그래픽) | Preferences → System → **GPU Backend = OpenGL**, Preferences → Save & Load → **Load UI 끄기**(이 저장소의 `.blend`는 화면 없이 저장되어 UI가 깨질 수 있음), 근본적으로는 그래픽 드라이버 업데이트 |
| `bpy.data.libraries.write()`에 Scene을 넘기면 강제 종료 | 쓰지 말 것 (README_UNREAL 9장) |

### 다음 작업 우선순위 (제안)

1. **언리얼 프로젝트 정하기** → 에셋 임포트, 숨기·수리·잠수함 상태 교체 블루프린트 (README_UNREAL 6장에 설계 있음)
2. 망가진 Mk2 잠수함(외부·선실) 텍스처 굽기 — 진행용·수리된 잠수함은 언리얼 타일링 재질을 슬롯에 입히는 방식
3. 다이버 추가 동작(사다리 등; 숨기·피격·사망·도망은 v3에서 완료) — 스크립트 키 애니메이션은 품질 한계가 있어 리타게팅(마켓플레이스·Mixamo)이나 Control Rig 권장
4. 무거운 모델 LOD(Nanite를 안 쓸 경우)
5. 저장소가 커지면 Git LFS 도입

---

## 저장소 메모

- 수동 백업 폴더(`Source/_backup_*`)와 Blender 자동 백업(`*.blend1`)은 저장소에서 제외했습니다(`.gitignore`). 버전 관리는 git 기록으로 합니다.
- `.blend` / FBX / PNG는 수정할 때마다 저장소가 커집니다. 수정이 잦아지면 **Git LFS** 사용을 고려하세요.
