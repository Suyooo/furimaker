#!/usr/bin/env python3

# Copyright (C) 2021 Suyooo

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import jaconv, os, pykakasi, sys, unicodedata, re

DEBUG = False

kks = pykakasi.kakasi()
kanji_re = re.compile("[㐀-䶵一-鿋豈-頻々]+")
ascii_re = re.compile("[ -~]+")

def print_furi(text, furi):
	return '\033[38;5;220m{furi}\n\033[0m{text}\n'.format(furi=furi, text=text)

def get_term_width(text):
    return sum([2 if unicodedata.east_asian_width(c)=='W' or unicodedata.east_asian_width(c)=='F' else 1 for c in text])

def romaji(s):
    return jaconv.kana2alphabet(jaconv.kata2alphabet(s.replace("ティ","ti").replace("ディ","di"))).replace("ー",".").replace("xtsu",".?").replace("'","").replace("「","\"").replace("」","\"").replace("、",",").replace("。",".")
def clean_test_string(string):
    string = re.escape(string.lower())
    splits = []
    for m in ascii_re.finditer(string):
        splits.append(m.span())
    
    res = ""
    for (s,e) in reversed(splits):
        res = string[s:e] + romaji(string[e:]) + res
        string = string[:s]
    
    if string != "": res = romaji(string) + res
    return res.replace("'", "")

def makefuri(lyricspath, furimode, inputs=[]):
    furiresult = ""
    with open(os.path.join(lyricspath, "jpn")) as kanjifile:
        k = [re.sub(r"(?<=[ -~])\u3000(?=[ -~])", " ", jaconv.normalize(l.strip()).replace(" ", "\u3000")) for l in kanjifile.readlines()]
    with open(os.path.join(lyricspath, "rom")) as romajifile:
        origr = [re.sub(r"\bwa\b", "ha", re.sub(r"\bo\b", "wo", re.sub(r"\be\b", "he", l.strip().lower().replace("'", "")))) for l in romajifile.readlines()]
        r = [l.replace(" ", "") for l in origr]
        
    for li in range(len(k)):
        # Find all Kanji in line
        splits = []
        for m in kanji_re.finditer(k[li]):
            splits.append(m.span())
        
        # Split up line at Kanji, into tuples of (string, is_kanji)
        j = [(k[li], False)]
        for (s,e) in reversed(splits):
            if s == 0:
                j = [(j[0][0][:e], True), (j[0][0][e:], False)] + j[1:]
            elif e == len(j[0][0]):
                j = [(j[0][0][:s], False), (j[0][0][s:], True)] + j[1:]
            else:
                j = [(j[0][0][:s], False), (j[0][0][s:e], True), (j[0][0][e:], False)] + j[1:]
        
        # Find reading for each Kanji tuple in Romaji line
        f = []
        gi = 0
        while gi < len(j):
            ogi = gi
            (s, is_kanji) = j[gi]
            if is_kanji:
                # Find previous non-kanji group
                if gi == 0:
                    prev_group = "^"
                else:
                    pgi = gi-1
                    prev_group = ""
                    while prev_group == "":
                        prev_group = "^" if pgi==-1 else j[pgi][0].replace("\u3000","").replace(" ","")
                        pgi -= 1
                if prev_group != "^":
                    prev_group = clean_test_string(prev_group)
                
                # Find next non-kanji group
                attempt_split = False
                if gi == len(j)-1:
                    next_group = "$"
                else:
                    ngi = gi+1
                    next_group = ""
                    while next_group == "":
                        if ngi < len(j) and j[ngi][1] == True:
                            # There's another Kanji group between this one and the next Kana group
                            # So these kanji are split by a space in the original lyrics, they're two seperate words
                            # Try to find both of them together, then attempt to split them
                            s = "".join([x[0] for x in j[ogi:ngi+1]])
                            gi = ngi
                            attempt_split = True
                        else:
                            next_group = "$" if ngi == len(j) else j[ngi][0].replace("\u3000","").replace(" ","")
                        ngi += 1
                if next_group != "$":
                    next_group = clean_test_string(next_group)
                
                # Match Romaji
                replacements = []
                m = re.search(prev_group + "(.{" + str(len(s)) + ",}?)" + next_group, r[li])
                if m == None:
                    if len(inputs) > 0:
                        replacements = [(s, inputs.pop(0))]
                    else:
                        if not DEBUG:
                                print("\x1b[38;2;255;0;0m\033[1mNo match\033[0m")
                                replacements = [(s, input("Manually enter romaji for " + s + " (" + "".join([x[0] for x in j]) + " / " + origr[li] + "): "))]
                        else:
                            print("\x1b[38;2;255;0;0m\033[1mNo match\033[0m")
                            replacements = [(s, "X")]
                else:
                    if attempt_split:
                        groups = s.split("\u3000")
                        if DEBUG: print("Splitting", groups, "/", m.group(1))
                        test_space_at = 1
                        while test_space_at < len(m.group(1)) and origr[li].find(m.group(1)[:test_space_at] + " " + m.group(1)[test_space_at:]) == -1:
                            test_space_at += 1
                        if len(groups) > 2 or test_space_at == len(m.group(1)):
                            replacements = [(s, m.group(1))]
                            if len(inputs) > 0:
                                inp = inputs.pop(0).split(" ")
                            else:
                                if not DEBUG:
                                    print("\x1b[38;2;255;0;0m\033[1mSplit unsuccessful", "(only two groups are possible to split automatically)" if len(groups) > 2 else "(couldn't find single space to split)" ,"\033[0m")
                                    inp = input("Manually split up the romaji \"" + m.group(1) + "\" for " + s + " (" + "".join([x[0] for x in j]) + " / " + origr[li] + "): ").split(" ")
                                else:
                                    inp = []
                            if len(inp) == len(groups):
                                replacements = zip(groups, inp)
                        else:
                            if DEBUG: print("Split successful")
                            split = [m.group(1)[:test_space_at], m.group(1)[test_space_at:]]
                            replacements = zip(groups, split)
                    else:
                        replacements = [(s, m.group(1))]
                    r[li] = r[li][m.span(1)[1]:]
                        
                for rep in replacements:
                    replacements_inner = [rep]
                    if len(rep[0]) > 1:
                        # Test whether Kanji that are next to each other could be seperate words using KaKaSi
                        kanjisplit = kks.convert(rep[0])
                        if len(kanjisplit) > 1:
                            if DEBUG: print("Possible kanji split:",kanjisplit)
                            if "".join([x["hepburn"] for x in kanjisplit if x["orig"] != "\u3000"]) == rep[1]:
                                # Complete split
                                replacements_inner = [(x["orig"], x["hepburn"]) for x in kanjisplit]
                            elif kanjisplit[0]["hepburn"] == rep[1][:len(kanjisplit[0]["hepburn"])]:
                                # Only split off first match (for example if the second kanji is part of a verb)
                                replacements_inner = [(kanjisplit[0]["orig"], kanjisplit[0]["hepburn"]), (rep[0][len(kanjisplit[0]["orig"]):], rep[1][len(kanjisplit[0]["hepburn"]):])]
                            elif kanjisplit[-1]["hepburn"] == rep[1][len(rep[1])-len(kanjisplit[-1]["hepburn"]):]:
                                # Only split off last match
                                replacements_inner = [(rep[0][:len(rep[0])-len(kanjisplit[-1]["orig"])], rep[1][:len(rep[1])-len(kanjisplit[-1]["hepburn"])]), (kanjisplit[-1]["orig"], kanjisplit[-1]["hepburn"])]
                    
                    for (old, new) in replacements_inner:
                        if DEBUG: print(old,"->",new)
                        if furimode == "K":
                            f.append((old, jaconv.z2h(jaconv.alphabet2kata(new))))
                        elif furimode == "H":
                            f.append((old, jaconv.alphabet2kana(new)))
                        elif furimode == "R":
                            f.append((old, new))
                    
                if DEBUG: 
                    print("  j: ", j)
                    print("  rom:     ", r[li])
                    print("  current: ", (s, is_kanji))
                    print("  test for:", prev_group + "(.+?)" + next_group)
                    print()
            else:
                f.append((s, ""))
            gi += 1
        
        # Output
        if len(f) == 1 and f[0][0] == "":
            furiresult += "\n"
        else:
            furiline = ""
            kanjiline = ""
            for (kanji, furi) in f:
                f_width = get_term_width(furi)
                k_width = get_term_width(kanji)
                m_width = max(f_width, k_width)
                furiline += furi + " "*(m_width-f_width)
                kanjiline += kanji + " "*(m_width-k_width)
                
            furiline = furiline.rstrip()
            kanjiline = kanjiline.rstrip()
            furiresult += print_furi(kanjiline, furiline)
    
    if len(inputs) > 0: print("\x1b[38;2;255;0;0m\033[1mWARNING: Leftover inputs\033[0m")
    return furiresult.strip()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: furiprint.py <lyrics folder> [furigana mode (K/H/R)] [debug mode (0/1)]")

    MODE = sys.argv[2] if len(sys.argv) >= 3 else "H"
    if MODE not in ["K","H","R"]:
        print("Invalid furigana mode, must be K (half-width Katakana), H (full-width Hiragana) or R (Romaji)")
        quit()    
    DEBUG = True if len(sys.argv) >= 4 and sys.argv[3] == "1" else False
    print(makefuri(sys.argv[1], MODE, sys.argv[4:]))
