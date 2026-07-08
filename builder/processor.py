import os
import subprocess
from fontTools.ttLib import TTFont
from fontTools.merge import Merger
from fontTools.ttLib.tables._c_m_a_p import cmap_format_4, cmap_format_12

def get_priority(cp):
    # 0. Flags (국기 기호 - 26개 알파벳. 하나라도 덮어씌워지면 모든 국기 조합이 박살나므로 무조건 최우선순위 9999 부여)
    if 0x1F1E6 <= cp <= 0x1F1FF: return 9999 

    # 1. Faces, Emotions, and Hands
    if 0x1F600 <= cp <= 0x1F64F: return 1000  # Emoticons
    if 0x1F900 <= cp <= 0x1F9FF: return 990   # Supplemental Faces/Hands
    if 0x1FA70 <= cp <= 0x1FAFF: return 980   # Symbols Extended-A
    
    # 2. Animals, Nature, and Food
    if 0x1F400 <= cp <= 0x1F4FF: return 800
    if 0x1F300 <= cp <= 0x1F3FA: return 750
    
    # 3. Transport, Map, and others
    if 0x1F680 <= cp <= 0x1F6FF: return 700
    
    # 4. 기타 Plane 1 이모지
    if 0x10000 <= cp < 0x20000: return 100
    return 0

def process_fonts(base_font_path, emoji_font_path, output_path, progress_callback=None):
    if progress_callback: progress_callback("[1/4] Reading base and emoji fonts...")
    
    emoji_font = TTFont(emoji_font_path)
    base_font = TTFont(base_font_path)
    
    # We want to extract the glyph mapping from the emoji font.
    cmap = emoji_font.getBestCmap()
    if not cmap:
        raise Exception("Emoji font does not have a valid cmap table.")
        
    migration_plan = {}
    for cp, glyphname in cmap.items():
        if cp < 0x10000 or cp >= 0x20000: continue
        priority = get_priority(cp)
        if priority == 0: continue
        
        target_low = 0xDC00 + (cp - 0x10000) % 0x400
        if target_low not in migration_plan or priority > migration_plan[target_low][0]:
            migration_plan[target_low] = (priority, glyphname)
            
    if progress_callback: progress_callback(f"[2/4] Remapping {len(migration_plan)} emojis to Low Surrogate area...")
    
    new_cmap = {}
    
    # 1. Plane 1 오리지널 코드포인트와 Low Surrogate 코드포인트 모두 매핑 (GSUB 리거처 및 최신 엔진 호환성)
    for target_low, (priority, glyphname) in migration_plan.items():
        new_cmap[target_low] = glyphname
        
    for cp, glyphname in cmap.items():
        if 0x10000 <= cp < 0x20000 and get_priority(cp) > 0:
            new_cmap[cp] = glyphname
            
    # 2. 완벽한 Zero-Width(폭 0) 글리프 생성
    glyph_order = emoji_font.getGlyphOrder()
    if "zerowidth" not in glyph_order:
        glyph_order.append("zerowidth")
        emoji_font.setGlyphOrder(glyph_order)
        from fontTools.ttLib.tables._g_l_y_f import Glyph
        g = Glyph()
        g.numberOfContours = 0
        emoji_font['glyf']['zerowidth'] = g
        emoji_font['hmtx']['zerowidth'] = (0, 0)
        
        # GDEF가 있다면 Mark(3)로 지정하여 GSUB 리거처가 무시할 수 있도록 시도
        if 'GDEF' in emoji_font and hasattr(emoji_font['GDEF'].table, 'GlyphClassDef'):
            emoji_font['GDEF'].table.GlyphClassDef.classDefs["zerowidth"] = 3
            
    # High Surrogate 영역(U+D800 ~ U+DBFF)을 Zero-Width로 매핑하여 찌꺼기 완벽 제거
    for cp in range(0xD800, 0xDC00):
        new_cmap[cp] = "zerowidth"
        
    # Clear existing cmaps in emoji font and replace with the new mapped emojis
    emoji_font['cmap'].tables = []
    
    new_subtable_4 = cmap_format_4(4)
    new_subtable_4.platformID = 3
    new_subtable_4.platEncID = 1
    new_subtable_4.language = 0
    new_subtable_4.cmap = {k: v for k, v in new_cmap.items() if k <= 0xFFFF}
    emoji_font['cmap'].tables.append(new_subtable_4)
    
    new_subtable_12 = cmap_format_12(12)
    new_subtable_12.platformID = 3
    new_subtable_12.platEncID = 10
    new_subtable_12.language = 0
    new_subtable_12.cmap = new_cmap
    emoji_font['cmap'].tables.append(new_subtable_12)
    
    # 3. 국기 조합용 알파벳(Regional Indicators)의 좌우 공백을 제거하여 바짝 붙임
    scale = 0.6  # 글자 크기는 60%로 유지
    padding = 60 # 글자 사이의 아주 좁은 간격 (양옆 30씩)
    for cp in range(0x1F1E6, 0x1F200):
        if cp in cmap:
            glyph_name = cmap[cp]
            if glyph_name in emoji_font['glyf']:
                glyph = emoji_font['glyf'][glyph_name]
                glyph.expand(emoji_font['glyf'])  # 좌표 데이터 로드
                
                if hasattr(glyph, "coordinates") and len(glyph.coordinates) > 0:
                    # 1단계: 스케일링
                    for i in range(len(glyph.coordinates)):
                        x, y = glyph.coordinates[i]
                        glyph.coordinates[i] = (int(x * scale), int(y * scale))
                    
                    # 2단계: 여백(Bounding Box)을 계산하여 왼쪽으로 바짝 당김
                    min_x = min(x for x, y in glyph.coordinates)
                    max_x = max(x for x, y in glyph.coordinates)
                    ink_width = max_x - min_x
                    
                    shift_x = (padding // 2) - min_x
                    for i in range(len(glyph.coordinates)):
                        x, y = glyph.coordinates[i]
                        glyph.coordinates[i] = (x + shift_x, y)
                    
                    # 3단계: 폰트의 실제 차지하는 폭(Advance Width)을 타이트하게 재설정
                    new_adv = ink_width + padding
                    emoji_font['hmtx'].metrics[glyph_name] = (new_adv, padding // 2)
    
    # 병합 충돌 방지를 위해 필수 테이블을 제외한 모든 메타데이터 테이블 삭제 (GSUB, GDEF는 국기/조합 이모지를 위해 유지)
    keep_tables = ['cmap', 'glyf', 'loca', 'hmtx', 'hhea', 'maxp', 'head', 'OS/2', 'post', 'name', 'CFF ', 'CFF2', 'cvt ', 'fpgm', 'prep', 'GSUB', 'GDEF']
    for t in list(emoji_font.keys()):
        if t not in keep_tables:
            del emoji_font[t]
            
    # 4. Base font의 UPEM에 맞춰 Emoji 폰트 전체 스케일링 (fontTools 병합 시 UPEM 불일치 방지)
    base_upem = base_font['head'].unitsPerEm
    emoji_upem = emoji_font['head'].unitsPerEm
    if base_upem != emoji_upem:
        if progress_callback: progress_callback(f"Scaling UPEM from {emoji_upem} to {base_upem}...")
        upem_scale = base_upem / emoji_upem
        for glyph_name in emoji_font['glyf'].keys():
            glyph = emoji_font['glyf'][glyph_name]
            glyph.expand(emoji_font['glyf'])
            if hasattr(glyph, "coordinates"):
                for i in range(len(glyph.coordinates)):
                    x, y = glyph.coordinates[i]
                    glyph.coordinates[i] = (int(x * upem_scale), int(y * upem_scale))
        for glyph_name in emoji_font['hmtx'].metrics.keys():
            adv, lsb = emoji_font['hmtx'].metrics[glyph_name]
            emoji_font['hmtx'].metrics[glyph_name] = (int(adv * upem_scale), int(lsb * upem_scale))
        emoji_font['head'].unitsPerEm = base_upem
            
    import tempfile
    temp_dir = tempfile.gettempdir()
    temp_emoji = os.path.join(temp_dir, os.path.basename(output_path) + ".emoji.ttf")
    emoji_font.save(temp_emoji)
    emoji_font.close()
    
    if progress_callback: progress_callback("[3/4] Merging fonts and auto-scaling glyphs...")
    
    from fontTools.merge import Options
    options = Options()
    options.drop_tables = ['gasp', 'vhea', 'vmtx', 'LTSH', 'VDMX', 'hdmx', 'DSIG', 'HVAR', 'STAT', 'VVAR', 'fvar', 'gvar', 'cvar', 'BASE', 'meta']
    
    try:
        merger = Merger(options=options)
        merged_font = merger.merge([base_font_path, temp_emoji])
    except Exception as e:
        if progress_callback: progress_callback(f"GSUB merge conflict detected with this font ({type(e).__name__}). Retrying without emoji ligatures...")
        # Fallback: Delete GSUB and GDEF from emoji_font, save again, and merge
        emoji_font = TTFont(temp_emoji)
        for t in ['GSUB', 'GDEF']:
            if t in emoji_font:
                del emoji_font[t]
        emoji_font.save(temp_emoji)
        emoji_font.close()
        
        merger = Merger(options=options)
        merged_font = merger.merge([base_font_path, temp_emoji])
    
    # --- [BUG FIX] Restore Vertical Metrics ---
    # fontTools.merge가 메트릭스를 최대값으로 덮어씌우는 것을 방지하고 Base Font의 원본 레이아웃을 100% 보존
    original_base = TTFont(base_font_path)
    if 'hhea' in original_base and 'hhea' in merged_font:
        merged_font['hhea'] = original_base['hhea']
    if 'OS/2' in original_base and 'OS/2' in merged_font:
        merged_font['OS/2'] = original_base['OS/2']
        # 카카오톡(Windows GDI)에서 폰트가 숨겨지거나 비활성화(회색) 처리되는 것을 방지하기 위해 필수 코드페이지 강제 할당
        # Bit 0: Latin 1 (필수 안하면 숨겨짐), Bit 19: Korean Wansung (필수 안하면 회색 처리)
        merged_font['OS/2'].ulCodePageRange1 |= (1 << 0) | (1 << 19)
    original_base.close()
    # ------------------------------------------
    
    # Add Winemoji to the name records
    if 'name' in merged_font:
        for record in merged_font['name'].names:
            if record.nameID in (1, 3, 4, 6): 
                try:
                    string = record.toUnicode()
                    if "Winemoji" not in string:
                        if record.nameID == 6:
                            new_string = (string + "Winemoji").replace(" ", "")
                        else:
                            new_string = (string + " Winemoji")
                        record.string = new_string.encode(record.getEncoding())
                except UnicodeDecodeError:
                    pass
            if record.nameID == 0: # Copyright
                try:
                    string = record.toUnicode()
                    if "Winemoji" not in string:
                        new_string = string + " | Emoji patched by Winemoji (SIL OFL 1.1)"
                        record.string = new_string.encode(record.getEncoding())
                except UnicodeDecodeError:
                    pass
                
    temp_merged = os.path.join(temp_dir, os.path.basename(output_path) + ".merged.ttf")
    merged_font.save(temp_merged)
    merged_font.close()
    base_font.close()
    
    if os.path.exists(temp_emoji): os.remove(temp_emoji)
    
    if progress_callback: progress_callback("[4/4] Optimizing and subsetting final font...")
    
    cmd = [
        "pyftsubset",
        temp_merged,
        "--output-file=" + output_path,
        "--unicodes=*",
        "--layout-features=*",
        "--glyph-names",
        "--symbol-cmap",
        "--legacy-cmap",
        "--notdef-glyph",
        "--notdef-outline",
        "--recommended-glyphs",
        "--name-IDs=*",
        "--name-legacy",
        "--name-languages=*"
    ]
    
    # Run pyftsubset
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # --- [BUG FIX] Force essential Code Page Bits for Windows GDI (After pyftsubset) ---
    # pyftsubset가 OS/2 테이블을 임의로 재계산하여 비트를 날려버리는 것을 방지하기 위해 최종 파일에 다시 적용
    final_font = TTFont(output_path)
    if 'OS/2' in final_font:
        final_font['OS/2'].ulCodePageRange1 |= (1 << 0) | (1 << 19)
        final_font.save(output_path)
    final_font.close()
    # -----------------------------------------------------------------------------------
    
    if os.path.exists(temp_merged): os.remove(temp_merged)
        
    if progress_callback: progress_callback(f"Build completed successfully: {output_path}")

def build_winemoji(base_font_path, emoji_font_path, output_path, progress_callback=None):
    process_fonts(base_font_path, emoji_font_path, output_path, progress_callback)
