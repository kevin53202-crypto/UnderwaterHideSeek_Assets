# 작업 기록 — 바닷속 숨바꼭질 에셋 (전체)

> 지금까지 진행한 작업 전체를 정리한 문서입니다. 날짜별 상세 내용은 `2026-11-09.md` 같은 날짜 파일을 보세요.
> 언리얼에서 에셋을 쓰는 방법은 `README_UNREAL.md`에 있습니다.

- 마지막 정리: 2026-11-16 (다이버 애니메이션 v2, 상세는 `2026-11-16.md`)
- 폴더: `C:\Users\0\Documents\UnderwaterHideSeek_Assets\`
- 제작 도구: Blender 5.2.3 LTS (Blender MCP 또는 Blender 백그라운드 실행 + Python 스크립트)

---

## 1. 게임 개요

- 언리얼 엔진용 **비대칭 숨바꼭질** (데드 바이 데이라이트 참고).
- 이야기: 잠수함이 고장 나서, 플레이어(다이버)들이 부품을 모아 수리하고 탈출합니다.
- 술래: 기괴한 심해 생물 NPC.
- 맵 아이디어: 해저 브라인 호수(안에 숨으면 은신), 동굴, 난파선, 방파제, 고래 사체(오래 숨어 있으면 터짐).
- 이 게임용 언리얼 프로젝트는 아직 정해지지 않았습니다. 기존 프로젝트(ShootingCPP, TPSProject, test_1)는 건드리지 않습니다.

---

## 2. 에셋 현황

### 정적 메시 (`SM_*.fbx`) — 2026-11-02 제작

| 분류 | 에셋 |
|---|---|
| 다이버 장비 | 손전등(`SM_DiveLight`, on/off 소켓), 산소통, BCD, 탱크 밴드, 마스크, 오리발, 레귤레이터 |
| 수집 아이템 | 배터리, 밸브 파이프, 기어, 전선 릴, 퓨즈 모듈 + (2026-11-16) 프로펠러 날, 선체 패치판, CO2 스크러버 카트리지, 회로 기판 + 잠수함 돔 유리, 모터 회전자, 방수액, 구리선, 용접기 (`build_parts3.py`) |
| 맵 소품 | 해저 가로등 `SM_StreetLamp` (2026-11-16, `SOCKET_Light`) |
| 맵 소품: 숨는 장소 | (2026-11-18) **고래 뼈대** `SM_WhaleSkeleton` (살 없이 뼈만, 부러진 갈비뼈 틈으로 흉곽 안에 숨기, `build_whale_skeleton.py` — 썩은 사체 버전은 폐기), **브라인 호수** `SM_BrinePool` + 수면 `SM_BrinePool_Surface` (`build_brine.py`), **난파선** `SM_Shipwreck` (기운 트롤 어선, 화물칸·조타실에 숨기, `build_shipwreck.py`) |
| 돔 유리 조각 | `SM_DomeShard_1~6` (2026-11-16, `build_dome_shards.py`) — 6개를 모아 `SM_Submarine`의 `SOCKET_DomeShard_1~6`에 붙이면 돔 완성. 기본형 잠수함은 돔 유리 없음 |
| 잠수함 Mk2 | **새 디자인 고품질 잠수함 3종** (2026-11-16, `build_sub2.py`): `SM_Sub2`, `SM_Sub2_Wrecked`, `SM_Sub2_Repaired` + 전용 부품 `SM_Sub2_PropBlade`, `SM_Sub2_HullPatch`. 선실·해치·정비 칸 문·돔 조각은 기존 것을 같이 씀 |
| 잠수함 Mk2 선실 | **Mk2 전용 선실 3종** (2026-11-18, `build_sub2_interior.py`): `SM_Sub2_Interior` / `_Wrecked` / `_Repaired` + `SM_Sub2_LockerDoor`, `SM_Sub2_PowerLever`. 흰·주황 현대식 배치, 소켓 이름은 기존과 같음 |
| 녹슨 잠수함 | `SM_Submarine_Rusted` (2026-11-16) — 기존 잠수함 망가진 버전 + 선체 전체 녹슨 색 |
| 유리 가루 | `SM_GlassPowder` (2026-11-16, `build_glass_powder.py`) — 돔 유리를 만드는 다른 수집 방식(가루 더미 + 유리 알갱이) |
| 잠수함 | **상태별 3종**(2026-11-16): 기본형 `SM_Submarine`/`SM_Sub_Interior`, 망가진 `*_Wrecked`, 수리된 `*_Repaired` (`build_sub_variants.py`). 외부(`SM_Submarine`, 수리 지점 4곳 + 탈출 해치), 내부(`SM_Sub_Interior`), 움직이는 부품 4개(해치 뚜껑, 정비 칸 문, 사물함 문, 전원 레버), 상호작용 소켓 |

### 캐릭터 (`SK_*.fbx`, 뼈대·애니메이션 포함)

| 캐릭터 | 현재 버전 | 상태 |
|---|---|---|
| `SK_Diver` 주인공 다이버 | v2 (2026-11-09), 애니메이션 v2 (2026-11-16) | 모델 완료. 애니메이션 9개 v2(키 포즈 + 떠 있기 레이어) — **사용자: "만족스럽지 않지만 일단 마무리"**, 나중에 다시 다룰 수 있음 |
| `SK_Gigantura` 기간투라 | v3 괴물화 버전 (2026-11-09) | 사용자 확인 완료("지금 상태 좋음") |
| `SK_DeepSeaEel` 심해 뱀장어 | v2 (2026-11-09) | 완료 |
| `SK_Kraken` 크라켄 | v1 (2026-11-09 신규) | 완료, 피드백 대기 |
| `SK_GiantIsopod` 거대 등각류 | v4 (2026-11-20 표면 디테일·갈색) | 완료 |

- 캐릭터마다 재질 1개(`M_<이름>`) + 4096 텍스처 4장(`Textures/T_<이름>_BaseColor/Normal/Roughness/Emissive.png`).
- 모든 캐릭터는 Blender −Y 방향을 바라봅니다.

---

## 3. 폴더와 도구

```
UnderwaterHideSeek_Assets/
├── README_UNREAL.md      ← 언리얼 사용 가이드 (팀원·AI용)
├── WORK_LOG.md           ← 이 문서 (전체 기록)
├── 2026-11-09.md         ← 날짜별 작업 기록
├── SM_*.fbx / SK_*.fbx
├── Textures/
└── Source/
    ├── DiveGear_Scene.blend          ← 모든 모델이 들어 있는 작업 씬
    ├── <모델명>.blend                 ← 모델별 원본
    ├── _backup_2026-11-09_monsters_v1/  ← 2026-11-09 작업 전 백업들
    └── _tools/
        ├── mk.py, rig.py, split_models.py, bake_textures.py   ← 공통 도구
        ├── horror.py, horror2.py                               ← 괴물용 모델링·셰이더 도우미
        ├── build_gigantura_v3.py (현재) / _v2 / (v1: build_gigantura.py)
        ├── build_eel_v2.py (현재) / (v1: build_eel.py)
        ├── build_kraken.py, build_isopod.py
        ├── build_diver_v2.py, build_diver_anims.py (v1, 사용 안 함)
        ├── anim_kit.py + build_diver_anims_v3.py   ← 다이버 애니메이션 v3 (이 순서로 exec; v2는 diver_poses.py + build_diver_anims_v2.py)
        └── monsters_v2_pipeline.py   ← uv_prep() / finalize() (모든 캐릭터 공통)
```

### 캐릭터 제작 순서 (공통)

1. 씬을 열고 `mk.py` → `rig.py` → `horror.py` → `horror2.py` → `build_<이름>.py` 실행
2. `monsters_v2_pipeline.py`의 `uv_prep(["SK_<이름>_Body"])` → 씬 저장
3. 텍스처 굽기: `blender -b --factory-startup --python Source/_tools/bake_textures.py -- Source/DiveGear_Scene.blend SK_<이름>_Body <이름> 4096`
4. `finalize(["SK_<이름>_Body"])` → 구운 재질로 교체, 삼각화, `SK_<이름>.fbx` 내보내기 → 씬 저장
5. `split_models.py`로 모델별 .blend 분리 (결과 파일 이름을 `<이름>.blend`로 바꿔 Source에 복사)

### 지켜야 할 규칙

- 모델을 완성하면 **모델마다 언리얼용 FBX를 따로 내보낸다.**
- 새로 만들거나 바꾸면 **`README_UNREAL.md`(4장 표, 7장 JSON)를 같이 고친다.**
- `bpy.data.libraries.write()`에 Scene을 넘기지 않는다(Blender 강제 종료됨).
- 위험한 작업 전에는 씬을 먼저 저장하거나 백업한다.
- **열려 있는 Blender 창의 씬이 오래된 상태일 수 있다.** 백그라운드로 씬을 고친 뒤에는, 예전에 열어 둔 창에서 저장하면 새 작업이 덮어써진다.

---

## 4. 남은 일 / 알려진 문제

- [ ] **다이버 수영 동작 수정 (사용자 지시, 2026-11-23, 1순위)**: 팀 게임 빌드에서 수영 움직임이 부자연스러움. `DV_Swim` / `DV_SwimFast` / `DV_SwimIdle` 수정. 자세한 방법은 README.md "다음 작업 우선순위" 0번.

- [x] 잠수함 Mk3 "만타" 삭제 (2026-11-18, 사용자 결정: 흰색 Mk2 `SM_Sub2`로 진행). FBX 18개·.blend 21개·`build_sub3.py`/`sub3_kit.py`는 `Source/_backup_2026-11-18_mk3_removed/`로 옮김, 작업 씬에서도 제거.
- [x] 흰색 Mk2 전용 선실 3종 + 사물함 문·전원 레버 (2026-11-18, `build_sub2_interior.py`). 재임포트로 소켓 17개 확인.
- [x] 맵 소품 1차 (2026-11-18): 고래 사체 2종, 브라인 호수 → 같은 날 **v2 디테일 작업**(사용자: "퀄리티가 다른 것에 비해 떨어짐"). 고래: 수염고래 두개골·고래수염·척추 돌기·상처·먹장어·게 등, 브라인: 조개 모양 홍합 덩어리·암석·하이드레이트·물결 등. v1은 `Source/_backup_2026-11-18_map_props_v1/`. 남은 맵 아이디어: 난파선, 해저 동굴, 방파제.
- [~] 다이버 애니메이션 v2 (2026-11-16): 키 포즈 + IK 접촉 + 관절별 시차 + 떠 있기 레이어. **사용자 평가: 만족스럽지 않음 → 일단 보류하고 다음 단계로.** 다시 할 때는 스크립트 키 자세만 다듬기보다 리타게팅(마켓플레이스/Mixamo 수중·상호작용 동작)이나 언리얼 Control Rig 등 방식 변경을 먼저 검토할 것.
  - 고칠 때: `build_diver_anims_v3.py`의 키 자세 값을 바꾸고 다시 exec → `rig.py`의 `export_skeletal(rig, "SK_Diver")`. 기준은 README **4-C**.
- [ ] 언리얼 쪽 마무리: Motion Warping, Two Bone IK, 수리 Montage 섹션·Notify (README 4-B).
- [ ] 다이버의 다른 동작(사물함 숨기, 사다리, 피격·사망, 해치 열기)은 아직 없음.
- [x] 잠수함 수리 부품 4개 + 수리 지점 추가 (2026-11-16): `SM_PropBlade`, `SM_HullPatch`, `SM_ScrubberCartridge`, `SM_CircuitBoard` → 수리 지점 총 8곳(외부 6, 내부 2). 도구 `build_repair_parts2.py`.
- [x] 잠수함 선실 디테일 (2026-11-16): `build_interior_detail.py` (IN_D_* 오브젝트, 다시 실행하면 지우고 새로 만듦). 내부 약 6천 → 2.2만 삼각형.
- [x] 거대 등각류 갈색 재도색 (2026-11-20): 회색·흰색 제거, 갈색 계열만(BaseColor 채도 0.53).
- [x] 괴물 4종 `*_Search` / `*_Hit` 애니메이션 추가 + 대기·헤엄 동작의 루트 위치 누락 버그 수정 (2026-11-20). `build_monster_anims_extra.py`.
- [x] 다이버 애니메이션 v3 (2026-11-20): 기존 9개 수정(좀비 팔 원인 = 리그 위치 무시한 IK 목표, 꼿꼿이 선 떠 있기 → 수평 트림, 줍기 뒤집힘, 패널 거리) + 새 6개(`DV_SwimFast`, `DV_Hit`, `DV_Death`, `DV_Hide_Enter/_Idle/_Exit`). `build_diver_anims_v3.py`.
- [x] 크라켄 피드백: 사용자가 가장 좋은 퀄리티로 평가 → 같은 수준으로 다른 괴물 업그레이드 (2026-11-20).
- [x] 괴물 3종 크라켄 수준 업그레이드 (2026-11-20): 뱀장어 v3(`build_eel_v3.py`, 뼈 19), 기간투라 v4(`build_gigantura_v4.py`), 등각류 v4(`build_isopod_v4.py`). 실행 `dev/run_monster.py`.
- [x] 거대 등각류 v2: 사실적 Bathynomus 형태로 재제작, 3m, 뼈 69, 애니 3종, 4096 텍스처 (2026-11-19).
- [x] 거대 등각류 v3: v2 피드백(다리가 거미처럼 뻗음, 알약 같은 몸, 공 같은 눈, 단조로운 색) 반영 재제작 — 다리를 몸 아래로, 겹친 판·옆판, 머리 옆 납작한 겹눈, AO 구움 (2026-11-20).
- [x] 씬 텍스처 경로 수정: 괴물 4종 텍스처가 원작자 PC 절대경로(C:/Users/0/...)라 분홍색으로 보이던 문제 → `Source/_tools/dev/fix_texture_paths.py` (2026-11-20).
- [ ] 정적 에셋에 텍스처 없음(UV만 준비됨), 콜리전 없음(언리얼에서 설정).
- [ ] 무거운 메시 LOD 필요: 크라켄(약 13만), 기간투라(약 10만), 뱀장어(약 7만), 손전등·BCD·잠수함 외부.
- [ ] 블루프린트(README 6장 상호작용)는 아직 구현 안 함.
- [ ] Blender MCP 연결이 끊긴 상태(2026-11-09). 백그라운드 Blender로 작업 중.
- [x] 고래 사체 → **고래 뼈대**로 교체 (2026-11-18, 사용자: "사체가 별로, 썩은 살 없이 거대한 뼈만"). "오래 숨으면 터짐" 장치는 뼈대에 맞지 않아 없앰. 사체 파일은 `Source/_backup_2026-11-18_whale_carcass_v2/`.
- [x] 난파선 (2026-11-18): 24m 강철 트롤 어선, 좌현 18° 기울어짐, 화물칸(해치·선체 구멍)·조타실 숨는 곳. 남은 맵 아이디어: 해저 동굴, 방파제.
- [x] 난파선 v2 (2026-11-18, 사용자: "너무 깨끗함, 내부 단조로움"): 녹 얼룩·벗겨진 밑칠·따개비·갑판 퇴적물·녹슬어 뚫린 구멍·녹슨 난간, 조타실 가구, **선원실 신설**(침대·사물함·식탁·주방, 조타실 계단과 화물칸 문으로 연결), 화물칸 잡동사니. v1은 `Source/_backup_2026-11-18_before_shipwreck/build_shipwreck_v1.py`.
- [x] 난파선 v3 (2026-11-18, 사용자: "내부 텍스처가 너무 깨끗함, 외부 텍스처 구워 넣기"): 모든 재질에 녹·때·곰팡이 절차적 노드(`weather_bake.py`의 `weather()`, 실내 재질이 가장 진함), 실내 천장 녹 고드름, 철제 가구를 녹슨 금속으로. **4096 텍스처 3장 굽기**(`T_Shipwreck_*`) → FBX 재질 1개 + 해저·유리 슬롯.
- [x] 고래 뼈대·브라인 호수 텍스처 굽기 (2026-11-18): `weather()` 절차적 질감 → 4096 `T_WhaleSkeleton_*`, `T_BrinePool_*`. 브라인 수면은 반투명이라 굽지 않음.
- [x] 해저 동굴 (2026-11-18, `build_cave.py`): 앞 입구·굽은 통로·큰 방·좁은 뒤 통로·뒤 출구, 벽감·바위 뒤 숨는 곳, 발광 이끼·가이드 줄·산호 등, 텍스처 구움 `T_SeaCave_*`. 남은 맵 아이디어: 방파제.
- [x] 방파제 (2026-11-18, `build_breakwater.py`): 케이슨 6개·테트라포드 더미·배수관(양쪽 열림)·무너진 틈, 숨는 곳 5곳, 텍스처 구움 `T_Breakwater_*`. **작업 기록의 맵 아이디어 5개(브라인 호수, 동굴, 난파선, 방파제, 고래) 모두 완료.**
- [x] 테트라포드 단독 모델 (2026-11-18, `build_tetrapod.py`): 복셀 리메시로 합친 몸체, 부러진 다리·철근·균열·따개비·홍합, 2048 텍스처 `T_Tetrapod_*`. 방파제(`SM_Breakwater`)는 그대로.
