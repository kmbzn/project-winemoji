# 🍷 project-winemoji 😄

**Winemoji**는 리눅스 환경의 Wine 환경에서 카카오톡 등 윈도우 기반 앱을 사용할 때 이모지 폰트가 깨지는(tofu) 문제를 해결하기 위해 제작된 특수 목적 폰트입니다. 기존에 이러한 문제로 불편함을 겪고 있던 분들에게 최적의 사용 환경을 제공하는 것을 목표로 시작되었습니다.

## ✅ 설치 방법

1. 본 저장소에서 `Winemoji-NBG.ttf` 파일을 다운로드합니다.
2. 리눅스 시스템의 폰트 폴더로 파일을 이동합니다.
    ```bash
    mkdir -p ~/.local/share/fonts
    cp Winemoji-NBG.ttf ~/.local/share/fonts/
    ```
3. 폰트 캐시를 갱신합니다.
    ```bash
    fc-cache -fv
    ```

### 💬 카카오톡에 적용 방법
![](settings.png)
1. ⚙️ → **설정** → **화면** → **기본** → **글씨체** 메뉴로 이동합니다.
2. 글씨체 선택에서 **Winemoji NBG** (or **와인모지 NBG**)를 선택합니다.
3. 카카오톡을 재시작하면 한글과 이모지가 완벽하게 출력되는 것을 확인할 수 있습니다.
![](chat.png)

## 🧐 구현 원리

리눅스 Wine의 GDI 렌더러는 유니코드 Plane 1 이상의 이모지(`U+1Fxxx` 등)를 정상적으로 처리하지 못하는 고질적인 문제가 있습니다. 이를 해결하기 위해 본 프로젝트는 다음과 같은 공학적 우회로를 설계했습니다.

- **Low Surrogate 매핑:** Plane 1의 이모지 데이터들을 BMP(Basic Multilingual Plane) 영역 내의 **Low Surrogate (`U+DC00` ~ `U+DFFF`)** 대역으로 강제 이주시켰습니다.
- **서열 정리 로직:** 동일한 Surrogate 슬롯을 점유하려는 이모지들 간의 충돌을 방지하기 위해, 현대적 표정(🤣 등)에 높은 가중치를 부여하는 **Priority Logic**을 적용했습니다.
- **메트릭스 동기화:** 나눔바른고딕의 **Ascent 800 / Descent 200** 규격에 맞춰 이모지 크기를 일괄 조정하여 행간이 벌어지거나 윗부분이 잘리는 현상을 방지했습니다.

### How to build my own Winemoji? (Replication)

기본적으로 라이선스상 폰트 편집 문제에서 자유롭고, 카카오톡 PC버전에 적용했을 때 글꼴이 선명하게 렌더링되는 특징을 가진 나눔바른고딕 폰트 기반으로 제작하였으나, 이외의 다른 폰트를 base로 삼기를 원한다면 아래 절차를 따르십시오.

1. **준비:** FontForge를 설치하고 베이스가 될 폰트와 소스 이모지 폰트를 준비합니다.
2. **이름 변경:** 라이선스 준수 및 시스템 충돌 방지를 위해 **Font Info**에서 폰트 이름을 고유한 이름(예: `MyEmoji-NBG`)으로 변경합니다.
3. **스크립트 실행:** 아래의 FontForge 파이썬 스크립트를 실행하여 이모지를 Low Surrogate 영역으로 복사합니다.
    - *Tip: 서열(Priority) 함수를 통해 🤣(U+1F923)와 같은 이모지가 🔣(U+1F523)와 같은 이모지들에 비해 높은 priority를 갖도록 설정해야 합니다.*
4. **수동 교정:** 복사된 이모지들을 전체 선택하여 **Element → Transformations** 메뉴에서 베이스 폰트의 EM Size에 맞게 크기를 조절합니다.

## Fontforge Python Script
```py
import fontforge

def get_priority(cp):
    if (0x1F600 <= cp <= 0x1F64F) or (0x1F900 <= cp <= 0x1F9FF):
        return 120
    if (0x1F300 <= cp <= 0x1F5FF) or (0x1F1E6 <= cp <= 0x1F1FF):
        return 100
    if (0x1FA00 <= cp <= 0x1FAFF):
        return 80
    if (0x10000 <= cp < 0x20000):
        return 50
    return 0

def migrate_emojis():
    font = fontforge.activeFont()
    if not font: return

    font.reencode('UnicodeFull')
    migration_plan = {}

    print("Starting emoji mapping to Low Surrogate area...")

    for glyph in font.glyphs():
        cp = glyph.unicode
        if cp < 0x10000 or cp >= 0x20000: continue
        
        priority = get_priority(cp)
        if priority == 0: continue

        target_low = 0xDC00 + (cp - 0x10000) % 0x400
        
        if target_low not in migration_plan or priority > migration_plan[target_low][0]:
            migration_plan[target_low] = (priority, cp)

    count = 0
    for target_low, (priority, source_cp) in migration_plan.items():
        try:
            font.selection.select(source_cp)
            font.copy()
            
            if target_low not in font: font.createChar(target_low)
            font.selection.select(target_low)
            font.paste()
            
            count += 1
        except:
            continue

    font.changed = True
    font.redraw()
    print(f"Process complete: {count} emojis mapped.")
    fontforge.postError("Complete", f"{count} emojis have been mapped to Low Surrogate area. Please adjust metrics in the GUI.")

migrate_emojis()
```

## License

This font project is distributed under the **SIL Open Font License 1.1**.

- **NanumBarunGothic**: Copyright (c) 2013 NHN Corporation. Licensed under SIL OFL 1.1.
- **Noto Emoji**: Copyright (c) Google Inc. Licensed under SIL OFL 1.1.
- **Winemoji Modifications**: Copyright (c) 2025 by KeyBaseZone. Licensed under SIL OFL 1.1.

Permission is hereby granted, free of charge, to any person obtaining a copy of the Font Software, to use, study, copy, merge, embed, modify, redistribute, and sell modified and unmodified copies of the Font Software, subject to the conditions set forth in the SIL OFL 1.1.
