# Test Case Statistics

## Overall Summary

| Design Type | Cases | Total Violations | Unique Rules | Avg Violations/Case | Std Dev | Min | Max |
| ----------- | ----: | ---------------: | -----------: | ------------------: | ------: | --: | --: |
| Cell        |   255 |            3,690 |            4 |                14.5 |     4.2 |   6 |  26 |
| Polygon     |   332 |            1,620 |          332 |                 4.9 |    15.5 |   1 | 244 |
| Block       |     7 |            1,628 |           17 |               232.6 |   228.6 |  68 | 765 |

---

## Block Cases (7)

| Block | Instances | Nets | Die Area (um²) | Core Area (um²) | Die (W x H um) | Core (W x H um) |
| ------ | --------- | ---- | -------------- | --------------- | -------------- | --------------- |
| Block1 | 143 | 120 | 16.06 | 9.30 | 4.008 x 4.008 | 3.132 x 2.970 |
| Block2 | 62 | 43 | 8.99 | 4.08 | 2.998 x 2.998 | 2.160 x 1.890 |
| Block3 | 76 | 62 | 10.07 | 5.02 | 3.174 x 3.174 | 2.322 x 2.160 |
| Block4 | 107 | 81 | 13.45 | 7.58 | 3.668 x 3.668 | 2.808 x 2.700 |
| Block5 | 47 | 28 | 7.27 | 2.97 | 2.696 x 2.696 | 1.836 x 1.620 |
| Block6 | 155 | 101 | 17.94 | 11.02 | 4.236 x 4.236 | 3.402 x 3.240 |
| Block7 | 574 | 410 | 57.91 | 43.74 | 7.610 x 7.610 | 6.750 x 6.480 |

### Block DRC Violations

| Block | Total Violations | Rules Violated | Violation Breakdown |
| ------ | ---------------: | -------------: | ------------------- |
| Block1 | 244 | 14 | M1.S.2 (12), M1.S.4 (2), M2.S.7 (1), M3.S.2 (2), M4.AUX.1 (18), M4.AUX.2 (2), M4.S.5 (4), M5.AUX.1 (8), M6.AUX.1 (3), V0.M1.AUX.3 (37), V1.M1.EN.1 (11), V2.M3.AUX.2 (72), V4.M5.AUX.2 (48), V5.M6.AUX.2 (24) |
| Block2 | 68 | 9 | M1.S.2 (2), M4.AUX.1 (6), M4.AUX.2 (1), M4.S.5 (1), M5.AUX.1 (4), V0.M1.AUX.3 (12), V1.M1.EN.1 (2), V2.M3.AUX.2 (24), V4.M5.AUX.2 (16) |
| Block3 | 89 | 9 | M1.S.2 (5), M1.S.4 (1), M4.AUX.1 (6), M4.AUX.2 (1), M5.AUX.1 (4), V0.M1.AUX.3 (21), V1.M1.EN.1 (6), V2.M3.AUX.2 (27), V4.M5.AUX.2 (18) |
| Block4 | 147 | 13 | M1.S.2 (8), M3.S.2 (1), M4.AUX.1 (11), M4.AUX.2 (2), M4.S.4 (1), M4.S.5 (2), M5.AUX.1 (6), M6.AUX.1 (1), V0.M1.AUX.3 (20), V1.M1.EN.1 (4), V2.M3.AUX.2 (51), V4.M5.AUX.2 (34), V5.M6.AUX.2 (6) |
| Block5 | 68 | 10 | M1.S.2 (6), M1.S.6 (2), M3.S.2 (1), M4.AUX.1 (5), M4.AUX.2 (1), M5.AUX.1 (4), V0.M1.AUX.3 (9), V1.M1.EN.1 (5), V2.M3.AUX.2 (21), V4.M5.AUX.2 (14) |
| Block6 | 247 | 13 | M1.S.2 (12), M1.S.4 (1), M1.S.6 (4), M3.S.2 (3), M4.AUX.1 (18), M4.AUX.2 (4), M5.AUX.1 (8), M6.AUX.1 (4), V0.M1.AUX.3 (21), V1.M1.EN.1 (10), V2.M3.AUX.2 (78), V4.M5.AUX.2 (52), V5.M6.AUX.2 (32) |
| Block7 | 765 | 16 | M1.S.2 (25), M1.S.4 (21), M1.S.5 (14), M1.S.6 (34), M2.S.7 (4), M3.S.2 (15), M4.AUX.1 (54), M4.AUX.2 (9), M4.S.5 (1), M5.AUX.1 (12), M6.AUX.1 (6), V0.M1.AUX.3 (97), V1.M1.EN.1 (26), V2.M3.AUX.2 (225), V4.M5.AUX.2 (150), V5.M6.AUX.2 (72) |

---

## Cell Cases (255)

Standard-cell layouts with M0, M1, and V0 layers.

### Cell DRC Summary

| Statistic | Value |
| --------- | ----- |
| Cases | 255 |
| Total violations | 3690 |
| Min violations per case | 6 |
| Max violations per case | 26 |
| Avg violations per case | 14.5 |

### Cell Violation Types

| Rule | Total Violations | Cases Affected |
| ---- | ---------------: | -------------: |
| M1.S.4 | 370 | 182 / 255 |
| M2.S.4 | 17 | 17 / 255 |
| M2.S.7 | 7 | 7 / 255 |
| V0.M0.EN.5 | 3296 | 255 / 255 |

### Cell Per-Case Violations

| Case | Total | Rules | Breakdown |
| ---- | ----: | ----: | --------- |
| Cell1 | 13 | 2 | M1.S.4 (2), V0.M0.EN.5 (11) |
| Cell10 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell100 | 20 | 2 | M1.S.4 (1), V0.M0.EN.5 (19) |
| Cell101 | 16 | 2 | M1.S.4 (1), V0.M0.EN.5 (15) |
| Cell102 | 17 | 2 | M1.S.4 (1), V0.M0.EN.5 (16) |
| Cell103 | 19 | 2 | M1.S.4 (1), V0.M0.EN.5 (18) |
| Cell104 | 20 | 2 | M1.S.4 (1), V0.M0.EN.5 (19) |
| Cell105 | 19 | 2 | M1.S.4 (1), V0.M0.EN.5 (18) |
| Cell106 | 17 | 2 | M1.S.4 (1), V0.M0.EN.5 (16) |
| Cell107 | 20 | 2 | M1.S.4 (1), V0.M0.EN.5 (19) |
| Cell108 | 17 | 2 | M1.S.4 (1), V0.M0.EN.5 (16) |
| Cell109 | 18 | 2 | M1.S.4 (1), V0.M0.EN.5 (17) |
| Cell11 | 6 | 1 | V0.M0.EN.5 (6) |
| Cell110 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell111 | 12 | 1 | V0.M0.EN.5 (12) |
| Cell112 | 18 | 2 | M1.S.4 (1), V0.M0.EN.5 (17) |
| Cell113 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell114 | 12 | 1 | V0.M0.EN.5 (12) |
| Cell115 | 11 | 1 | V0.M0.EN.5 (11) |
| Cell116 | 11 | 1 | V0.M0.EN.5 (11) |
| Cell117 | 12 | 1 | V0.M0.EN.5 (12) |
| Cell118 | 13 | 1 | V0.M0.EN.5 (13) |
| Cell119 | 13 | 1 | V0.M0.EN.5 (13) |
| Cell12 | 8 | 1 | V0.M0.EN.5 (8) |
| Cell120 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell121 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell122 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell123 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell124 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell125 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell126 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell127 | 19 | 2 | M1.S.4 (2), V0.M0.EN.5 (17) |
| Cell128 | 21 | 2 | M1.S.4 (2), V0.M0.EN.5 (19) |
| Cell129 | 18 | 2 | M1.S.4 (1), V0.M0.EN.5 (17) |
| Cell13 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell130 | 17 | 2 | M1.S.4 (1), V0.M0.EN.5 (16) |
| Cell131 | 21 | 2 | M1.S.4 (2), V0.M0.EN.5 (19) |
| Cell132 | 21 | 2 | M1.S.4 (2), V0.M0.EN.5 (19) |
| Cell133 | 21 | 2 | M1.S.4 (2), V0.M0.EN.5 (19) |
| Cell134 | 22 | 2 | M1.S.4 (2), V0.M0.EN.5 (20) |
| Cell135 | 22 | 2 | M1.S.4 (2), V0.M0.EN.5 (20) |
| Cell136 | 11 | 2 | M1.S.4 (1), V0.M0.EN.5 (10) |
| Cell137 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell138 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell139 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell14 | 7 | 1 | V0.M0.EN.5 (7) |
| Cell140 | 11 | 2 | M1.S.4 (1), V0.M0.EN.5 (10) |
| Cell141 | 10 | 2 | M1.S.4 (1), V0.M0.EN.5 (9) |
| Cell142 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell143 | 18 | 2 | M1.S.4 (2), V0.M0.EN.5 (16) |
| Cell144 | 16 | 2 | M1.S.4 (2), V0.M0.EN.5 (14) |
| Cell145 | 16 | 2 | M1.S.4 (3), V0.M0.EN.5 (13) |
| Cell146 | 15 | 2 | M1.S.4 (3), V0.M0.EN.5 (12) |
| Cell147 | 14 | 2 | M1.S.4 (3), V0.M0.EN.5 (11) |
| Cell148 | 17 | 2 | M1.S.4 (2), V0.M0.EN.5 (15) |
| Cell149 | 18 | 2 | M1.S.4 (2), V0.M0.EN.5 (16) |
| Cell15 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell150 | 17 | 2 | M1.S.4 (2), V0.M0.EN.5 (15) |
| Cell151 | 15 | 2 | M1.S.4 (3), V0.M0.EN.5 (12) |
| Cell152 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell153 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell154 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell155 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell156 | 11 | 1 | V0.M0.EN.5 (11) |
| Cell157 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell158 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell159 | 11 | 1 | V0.M0.EN.5 (11) |
| Cell16 | 11 | 1 | V0.M0.EN.5 (11) |
| Cell160 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell161 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell162 | 25 | 2 | M1.S.4 (5), V0.M0.EN.5 (20) |
| Cell163 | 24 | 2 | M1.S.4 (6), V0.M0.EN.5 (18) |
| Cell164 | 23 | 2 | M1.S.4 (6), V0.M0.EN.5 (17) |
| Cell165 | 24 | 2 | M1.S.4 (6), V0.M0.EN.5 (18) |
| Cell166 | 26 | 2 | M1.S.4 (5), V0.M0.EN.5 (21) |
| Cell167 | 23 | 2 | M1.S.4 (7), V0.M0.EN.5 (16) |
| Cell168 | 23 | 2 | M1.S.4 (5), V0.M0.EN.5 (18) |
| Cell169 | 24 | 2 | M1.S.4 (7), V0.M0.EN.5 (17) |
| Cell17 | 7 | 1 | V0.M0.EN.5 (7) |
| Cell170 | 26 | 2 | M1.S.4 (5), V0.M0.EN.5 (21) |
| Cell171 | 15 | 2 | M1.S.4 (3), V0.M0.EN.5 (12) |
| Cell172 | 18 | 2 | M1.S.4 (1), V0.M0.EN.5 (17) |
| Cell173 | 16 | 2 | M1.S.4 (3), V0.M0.EN.5 (13) |
| Cell174 | 16 | 2 | M1.S.4 (3), V0.M0.EN.5 (13) |
| Cell175 | 19 | 2 | M1.S.4 (2), V0.M0.EN.5 (17) |
| Cell176 | 18 | 2 | M1.S.4 (2), V0.M0.EN.5 (16) |
| Cell177 | 19 | 2 | M1.S.4 (2), V0.M0.EN.5 (17) |
| Cell178 | 16 | 2 | M1.S.4 (3), V0.M0.EN.5 (13) |
| Cell179 | 16 | 2 | M1.S.4 (3), V0.M0.EN.5 (13) |
| Cell18 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell180 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell181 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell182 | 11 | 1 | V0.M0.EN.5 (11) |
| Cell183 | 11 | 1 | V0.M0.EN.5 (11) |
| Cell184 | 11 | 1 | V0.M0.EN.5 (11) |
| Cell185 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell186 | 11 | 1 | V0.M0.EN.5 (11) |
| Cell187 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell188 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell189 | 19 | 2 | M1.S.4 (3), V0.M0.EN.5 (16) |
| Cell19 | 8 | 2 | M1.S.4 (1), V0.M0.EN.5 (7) |
| Cell190 | 21 | 2 | M1.S.4 (3), V0.M0.EN.5 (18) |
| Cell191 | 20 | 2 | M1.S.4 (3), V0.M0.EN.5 (17) |
| Cell192 | 21 | 2 | M1.S.4 (3), V0.M0.EN.5 (18) |
| Cell193 | 20 | 2 | M1.S.4 (3), V0.M0.EN.5 (17) |
| Cell194 | 15 | 2 | M1.S.4 (2), V0.M0.EN.5 (13) |
| Cell195 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell196 | 16 | 2 | M1.S.4 (1), V0.M0.EN.5 (15) |
| Cell197 | 16 | 2 | M1.S.4 (3), V0.M0.EN.5 (13) |
| Cell198 | 16 | 2 | M1.S.4 (1), V0.M0.EN.5 (15) |
| Cell199 | 17 | 2 | M1.S.4 (1), V0.M0.EN.5 (16) |
| Cell2 | 13 | 2 | M1.S.4 (2), V0.M0.EN.5 (11) |
| Cell20 | 7 | 1 | V0.M0.EN.5 (7) |
| Cell200 | 19 | 2 | M1.S.4 (4), V0.M0.EN.5 (15) |
| Cell201 | 18 | 3 | M1.S.4 (4), M2.S.4 (1), V0.M0.EN.5 (13) |
| Cell202 | 18 | 3 | M1.S.4 (4), M2.S.4 (1), V0.M0.EN.5 (13) |
| Cell203 | 17 | 3 | M1.S.4 (4), M2.S.4 (1), V0.M0.EN.5 (12) |
| Cell204 | 16 | 3 | M1.S.4 (4), M2.S.4 (1), V0.M0.EN.5 (11) |
| Cell205 | 16 | 3 | M1.S.4 (4), M2.S.4 (1), V0.M0.EN.5 (11) |
| Cell206 | 16 | 3 | M1.S.4 (4), M2.S.4 (1), V0.M0.EN.5 (11) |
| Cell207 | 18 | 3 | M1.S.4 (4), M2.S.4 (1), V0.M0.EN.5 (13) |
| Cell208 | 18 | 3 | M1.S.4 (4), M2.S.4 (1), V0.M0.EN.5 (13) |
| Cell209 | 17 | 3 | M1.S.4 (4), M2.S.4 (1), V0.M0.EN.5 (12) |
| Cell21 | 8 | 2 | M1.S.4 (1), V0.M0.EN.5 (7) |
| Cell210 | 18 | 2 | M1.S.4 (2), V0.M0.EN.5 (16) |
| Cell211 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell212 | 11 | 2 | M1.S.4 (1), V0.M0.EN.5 (10) |
| Cell213 | 13 | 2 | M1.S.4 (1), V0.M0.EN.5 (12) |
| Cell214 | 18 | 2 | M1.S.4 (2), V0.M0.EN.5 (16) |
| Cell215 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell216 | 11 | 2 | M1.S.4 (1), V0.M0.EN.5 (10) |
| Cell217 | 18 | 2 | M1.S.4 (2), V0.M0.EN.5 (16) |
| Cell218 | 11 | 2 | M1.S.4 (1), V0.M0.EN.5 (10) |
| Cell219 | 18 | 2 | M1.S.4 (2), V0.M0.EN.5 (16) |
| Cell22 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell220 | 17 | 4 | M1.S.4 (1), M2.S.4 (1), M2.S.7 (1), V0.M0.EN.5 (14) |
| Cell221 | 22 | 3 | M1.S.4 (3), M2.S.4 (1), V0.M0.EN.5 (18) |
| Cell222 | 14 | 4 | M1.S.4 (1), M2.S.4 (1), M2.S.7 (1), V0.M0.EN.5 (11) |
| Cell223 | 22 | 3 | M1.S.4 (3), M2.S.7 (1), V0.M0.EN.5 (18) |
| Cell224 | 17 | 3 | M1.S.4 (1), M2.S.4 (1), V0.M0.EN.5 (15) |
| Cell225 | 19 | 4 | M1.S.4 (1), M2.S.4 (1), M2.S.7 (1), V0.M0.EN.5 (16) |
| Cell226 | 24 | 3 | M1.S.4 (3), M2.S.7 (1), V0.M0.EN.5 (20) |
| Cell227 | 14 | 3 | M1.S.4 (1), M2.S.4 (1), V0.M0.EN.5 (12) |
| Cell228 | 19 | 4 | M1.S.4 (1), M2.S.4 (1), M2.S.7 (1), V0.M0.EN.5 (16) |
| Cell229 | 16 | 4 | M1.S.4 (1), M2.S.4 (1), M2.S.7 (1), V0.M0.EN.5 (13) |
| Cell23 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell230 | 20 | 2 | M1.S.4 (3), V0.M0.EN.5 (17) |
| Cell231 | 20 | 2 | M1.S.4 (3), V0.M0.EN.5 (17) |
| Cell232 | 21 | 2 | M1.S.4 (3), V0.M0.EN.5 (18) |
| Cell233 | 20 | 2 | M1.S.4 (3), V0.M0.EN.5 (17) |
| Cell234 | 20 | 2 | M1.S.4 (3), V0.M0.EN.5 (17) |
| Cell235 | 21 | 2 | M1.S.4 (3), V0.M0.EN.5 (18) |
| Cell236 | 21 | 2 | M1.S.4 (3), V0.M0.EN.5 (18) |
| Cell237 | 20 | 2 | M1.S.4 (3), V0.M0.EN.5 (17) |
| Cell238 | 20 | 2 | M1.S.4 (3), V0.M0.EN.5 (17) |
| Cell239 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell24 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell240 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell241 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell242 | 13 | 2 | M1.S.4 (1), V0.M0.EN.5 (12) |
| Cell243 | 13 | 2 | M1.S.4 (1), V0.M0.EN.5 (12) |
| Cell244 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell245 | 13 | 2 | M1.S.4 (1), V0.M0.EN.5 (12) |
| Cell246 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell247 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell248 | 17 | 2 | M1.S.4 (1), V0.M0.EN.5 (16) |
| Cell249 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell25 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell250 | 15 | 1 | V0.M0.EN.5 (15) |
| Cell251 | 15 | 2 | M1.S.4 (1), V0.M0.EN.5 (14) |
| Cell252 | 15 | 2 | M1.S.4 (1), V0.M0.EN.5 (14) |
| Cell253 | 15 | 2 | M1.S.4 (1), V0.M0.EN.5 (14) |
| Cell254 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell255 | 15 | 1 | V0.M0.EN.5 (15) |
| Cell26 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell27 | 11 | 2 | M1.S.4 (2), V0.M0.EN.5 (9) |
| Cell28 | 15 | 2 | M1.S.4 (2), V0.M0.EN.5 (13) |
| Cell29 | 10 | 2 | M1.S.4 (2), V0.M0.EN.5 (8) |
| Cell3 | 10 | 2 | M1.S.4 (1), V0.M0.EN.5 (9) |
| Cell30 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell31 | 13 | 1 | V0.M0.EN.5 (13) |
| Cell32 | 13 | 1 | V0.M0.EN.5 (13) |
| Cell33 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell34 | 15 | 2 | M1.S.4 (2), V0.M0.EN.5 (13) |
| Cell35 | 15 | 2 | M1.S.4 (2), V0.M0.EN.5 (13) |
| Cell36 | 13 | 2 | M1.S.4 (1), V0.M0.EN.5 (12) |
| Cell37 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell38 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell39 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell4 | 10 | 2 | M1.S.4 (1), V0.M0.EN.5 (9) |
| Cell40 | 13 | 1 | V0.M0.EN.5 (13) |
| Cell41 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell42 | 13 | 1 | V0.M0.EN.5 (13) |
| Cell43 | 14 | 1 | V0.M0.EN.5 (14) |
| Cell44 | 15 | 2 | M1.S.4 (1), V0.M0.EN.5 (14) |
| Cell45 | 13 | 1 | V0.M0.EN.5 (13) |
| Cell46 | 14 | 1 | V0.M0.EN.5 (14) |
| Cell47 | 14 | 1 | V0.M0.EN.5 (14) |
| Cell48 | 14 | 2 | M1.S.4 (2), V0.M0.EN.5 (12) |
| Cell49 | 15 | 2 | M1.S.4 (1), V0.M0.EN.5 (14) |
| Cell5 | 13 | 2 | M1.S.4 (2), V0.M0.EN.5 (11) |
| Cell50 | 14 | 1 | V0.M0.EN.5 (14) |
| Cell51 | 17 | 1 | V0.M0.EN.5 (17) |
| Cell52 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell53 | 12 | 2 | M1.S.4 (1), V0.M0.EN.5 (11) |
| Cell54 | 12 | 2 | M1.S.4 (2), V0.M0.EN.5 (10) |
| Cell55 | 12 | 2 | M1.S.4 (2), V0.M0.EN.5 (10) |
| Cell56 | 12 | 2 | M1.S.4 (2), V0.M0.EN.5 (10) |
| Cell57 | 12 | 2 | M1.S.4 (2), V0.M0.EN.5 (10) |
| Cell58 | 10 | 2 | M1.S.4 (4), V0.M0.EN.5 (6) |
| Cell59 | 11 | 2 | M1.S.4 (2), V0.M0.EN.5 (9) |
| Cell6 | 13 | 2 | M1.S.4 (2), V0.M0.EN.5 (11) |
| Cell60 | 9 | 2 | M1.S.4 (2), V0.M0.EN.5 (7) |
| Cell61 | 12 | 2 | M1.S.4 (2), V0.M0.EN.5 (10) |
| Cell62 | 10 | 2 | M1.S.4 (2), V0.M0.EN.5 (8) |
| Cell63 | 12 | 2 | M1.S.4 (2), V0.M0.EN.5 (10) |
| Cell64 | 13 | 2 | M1.S.4 (1), V0.M0.EN.5 (12) |
| Cell65 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell66 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell67 | 13 | 2 | M1.S.4 (1), V0.M0.EN.5 (12) |
| Cell68 | 13 | 2 | M1.S.4 (1), V0.M0.EN.5 (12) |
| Cell69 | 13 | 2 | M1.S.4 (1), V0.M0.EN.5 (12) |
| Cell7 | 13 | 2 | M1.S.4 (2), V0.M0.EN.5 (11) |
| Cell70 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell71 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell72 | 14 | 2 | M1.S.4 (1), V0.M0.EN.5 (13) |
| Cell73 | 13 | 2 | M1.S.4 (1), V0.M0.EN.5 (12) |
| Cell74 | 17 | 2 | M1.S.4 (3), V0.M0.EN.5 (14) |
| Cell75 | 15 | 2 | M1.S.4 (3), V0.M0.EN.5 (12) |
| Cell76 | 16 | 2 | M1.S.4 (3), V0.M0.EN.5 (13) |
| Cell77 | 16 | 2 | M1.S.4 (3), V0.M0.EN.5 (13) |
| Cell78 | 17 | 2 | M1.S.4 (3), V0.M0.EN.5 (14) |
| Cell79 | 17 | 2 | M1.S.4 (3), V0.M0.EN.5 (14) |
| Cell8 | 13 | 2 | M1.S.4 (2), V0.M0.EN.5 (11) |
| Cell80 | 17 | 2 | M1.S.4 (2), V0.M0.EN.5 (15) |
| Cell81 | 17 | 2 | M1.S.4 (3), V0.M0.EN.5 (14) |
| Cell82 | 17 | 2 | M1.S.4 (3), V0.M0.EN.5 (14) |
| Cell83 | 16 | 1 | V0.M0.EN.5 (16) |
| Cell84 | 16 | 2 | M1.S.4 (1), V0.M0.EN.5 (15) |
| Cell85 | 17 | 2 | M1.S.4 (1), V0.M0.EN.5 (16) |
| Cell86 | 19 | 2 | M1.S.4 (1), V0.M0.EN.5 (18) |
| Cell87 | 15 | 1 | V0.M0.EN.5 (15) |
| Cell88 | 16 | 1 | V0.M0.EN.5 (16) |
| Cell89 | 18 | 2 | M1.S.4 (1), V0.M0.EN.5 (17) |
| Cell9 | 9 | 2 | M1.S.4 (1), V0.M0.EN.5 (8) |
| Cell90 | 16 | 1 | V0.M0.EN.5 (16) |
| Cell91 | 8 | 1 | V0.M0.EN.5 (8) |
| Cell92 | 8 | 1 | V0.M0.EN.5 (8) |
| Cell93 | 12 | 1 | V0.M0.EN.5 (12) |
| Cell94 | 10 | 1 | V0.M0.EN.5 (10) |
| Cell95 | 8 | 1 | V0.M0.EN.5 (8) |
| Cell96 | 9 | 1 | V0.M0.EN.5 (9) |
| Cell97 | 8 | 1 | V0.M0.EN.5 (8) |
| Cell98 | 7 | 1 | V0.M0.EN.5 (7) |
| Cell99 | 7 | 1 | V0.M0.EN.5 (7) |

---

## Polygon Cases (332)

Isolated polygon constructs, each testing a specific DRC rule along with closely related rules.

### Polygon DRC Summary

| Statistic | Value |
| --------- | ----- |
| Cases | 332 |
| Total violations | 1620 |
| Min violations per case | 1 |
| Max violations per case | 244 |
| Avg violations per case | 4.9 |

### Polygon Per-Case Violations

| Case | Target Rule | Total Violations | Rules Violated | Violation Breakdown |
| ---- | ----------- | ---------------: | -------------: | ------------------- |
| Polygon1 | ACTIVE.A.1A | 1 | 1 | ACTIVE.A.1A (1) |
| Polygon2 | ACTIVE.A.1B | 6 | 4 | ACTIVE.A.1B (1), ACTIVE.AUX.3 (1), ACTIVE.S.2B (1), ACTIVE.W.2 (3) |
| Polygon3 | ACTIVE.AUX.1 | 9 | 3 | ACTIVE.AUX.1 (2), PSELECT.ACTIVE.EN.1 (5), PSELECT.ACTIVE.EN.2 (2) |
| Polygon4 | ACTIVE.AUX.3 | 5 | 3 | ACTIVE.AUX.3 (1), ACTIVE.W.1 (2), ACTIVE.W.2 (2) |
| Polygon5 | ACTIVE.FIN.EX.1 | 1 | 1 | ACTIVE.FIN.EX.1 (1) |
| Polygon6 | ACTIVE.LUP.1 | 3 | 3 | ACTIVE.LUP.1 (1), ACTIVE.W.2 (1), GATE.S.3 (1) |
| Polygon7 | ACTIVE.S.1 | 1 | 1 | ACTIVE.S.1 (1) |
| Polygon8 | ACTIVE.S.2A | 7 | 5 | ACTIVE.S.2A (1), ACTIVE.S.2B (1), ACTIVE.W.2 (2), GATE.ACTIVE.EX.2 (1), GATE.S.3 (2) |
| Polygon9 | ACTIVE.S.2B | 18 | 6 | ACTIVE.S.2B (1), GATE.ACTIVE.AUX.3 (2), GATE.ACTIVE.EX.2 (2), GATE.S.1 (6), GATE.S.2 (3), GATE.S.3 (4) |
| Polygon10 | ACTIVE.W.1 | 2 | 2 | ACTIVE.W.1 (1), ACTIVE.W.2 (1) |
| Polygon11 | ACTIVE.W.2 | 1 | 1 | ACTIVE.W.2 (1) |
| Polygon12 | ACTIVE.W.3 | 2 | 2 | ACTIVE.A.1A (1), ACTIVE.W.3 (1) |
| Polygon13 | ACTIVE.WELL.EN.1 | 2 | 2 | ACTIVE.LUP.1 (1), ACTIVE.WELL.EN.1 (1) |
| Polygon14 | ACTIVE.WELL.S.4 | 1 | 1 | ACTIVE.WELL.S.4 (1) |
| Polygon15 | FIN.AUX.1 | 12 | 4 | FIN.AUX.1 (4), FIN.S.1 (2), FIN.W.1 (3), FIN.W.2 (3) |
| Polygon16 | FIN.S.1 | 1 | 1 | FIN.S.1 (1) |
| Polygon17 | FIN.W.1 | 1 | 1 | FIN.W.1 (1) |
| Polygon18 | FIN.W.2 | 1 | 1 | FIN.W.2 (1) |
| Polygon19 | GATE.ACTIVE.AUX.3 | 5 | 4 | ACTIVE.W.2 (1), GATE.ACTIVE.AUX.3 (1), GATE.S.3 (1), NSELECT.ACTIVE.EN.2 (2) |
| Polygon20 | GATE.ACTIVE.EX.1 | 3 | 3 | ACTIVE.W.2 (1), GATE.ACTIVE.EX.1 (1), GATE.S.3 (1) |
| Polygon21 | GATE.ACTIVE.EX.2 | 3 | 3 | ACTIVE.W.2 (1), GATE.ACTIVE.EX.2 (1), GATE.S.3 (1) |
| Polygon22 | GATE.ACTIVE.S.4 | 5 | 4 | ACTIVE.W.2 (1), GATE.ACTIVE.S.4 (1), GATE.S.1 (1), GATE.S.3 (2) |
| Polygon23 | GATE.AUX.1 | 6 | 4 | GATE.AUX.1 (2), GATE.S.1 (1), GATE.W.1 (2), GATE.W.2 (1) |
| Polygon24 | GATE.AUX.2 | 9 | 3 | GATE.AUX.2 (3), GATE.S.1 (3), GATE.S.3 (3) |
| Polygon25 | GATE.S.1 | 3 | 2 | GATE.S.1 (1), GATE.S.3 (2) |
| Polygon26 | GATE.S.2 | 4 | 3 | GATE.S.1 (1), GATE.S.2 (1), GATE.S.3 (2) |
| Polygon27 | GATE.S.3 | 1 | 1 | GATE.S.3 (1) |
| Polygon28 | GATE.W.1 | 2 | 2 | GATE.S.3 (1), GATE.W.1 (1) |
| Polygon29 | GATE.W.2 | 2 | 2 | GATE.S.3 (1), GATE.W.2 (1) |
| Polygon30 | GCUT.ACTIVE.S.1 | 3 | 3 | GATE.ACTIVE.EX.1 (1), GATE.S.3 (1), GCUT.ACTIVE.S.1 (1) |
| Polygon31 | GCUT.AUX.1 | 1 | 1 | GCUT.AUX.1 (1) |
| Polygon32 | GCUT.AUX.2 | 2 | 2 | GATE.S.3 (1), GCUT.AUX.2 (1) |
| Polygon33 | GCUT.AUX.3 | 5 | 4 | ACTIVE.W.2 (1), GATE.S.3 (1), GCUT.ACTIVE.S.1 (2), GCUT.AUX.3 (1) |
| Polygon34 | GCUT.GATE.EX.1 | 2 | 2 | GATE.S.3 (1), GCUT.GATE.EX.1 (1) |
| Polygon35 | GCUT.GATE.S.2 | 1 | 1 | GCUT.GATE.S.2 (1) |
| Polygon36 | GCUT.S.3 | 2 | 2 | GATE.S.3 (1), GCUT.S.3 (1) |
| Polygon37 | GCUT.W.1 | 2 | 2 | GATE.S.3 (1), GCUT.W.1 (1) |
| Polygon38 | LIG.A.1 | 1 | 1 | LIG.A.1 (1) |
| Polygon39 | LIG.GATE.A.3 | 7 | 5 | GATE.S.3 (1), LIG.A.1 (1), LIG.GATE.A.3 (1), LIG.GATE.AUX.1 (2), LIG.GATE.EX.1 (2) |
| Polygon40 | LIG.GATE.AUX.1 | 3 | 3 | GATE.S.3 (1), LIG.GATE.AUX.1 (1), LIG.GATE.EX.1 (1) |
| Polygon41 | LIG.GATE.EX.1 | 3 | 2 | GATE.S.3 (1), LIG.GATE.EX.1 (2) |
| Polygon42 | LIG.GATE.S.10 | 8 | 6 | GATE.S.1 (1), GATE.S.3 (2), GCUT.AUX.1 (1), GCUT.GATE.S.2 (1), LIG.GATE.S.10 (1), NSELECT.ACTIVE.EN.1 (2) |
| Polygon43 | LIG.GATE.S.9A | 2 | 2 | GATE.S.3 (1), LIG.GATE.S.9A (1) |
| Polygon44 | LIG.GATE.S.9B | 2 | 2 | GATE.S.3 (1), LIG.GATE.S.9B (1) |
| Polygon45 | LIG.GCUT.S.11 | 5 | 5 | GATE.S.3 (1), LIG.GATE.AUX.1 (1), LIG.GATE.EX.1 (1), LIG.GATE.S.9B (1), LIG.GCUT.S.11 (1) |
| Polygon46 | LIG.LISD.A.2 | 5 | 4 | LIG.LISD.A.2 (1), LIG.LISD.OV.1 (1), LISD.A.1 (1), LISD.W.1 (2) |
| Polygon47 | LIG.LISD.OV.1 | 4 | 4 | LIG.LISD.A.2 (1), LIG.LISD.OV.1 (1), LISD.A.1 (1), LISD.W.1 (1) |
| Polygon48 | LIG.LISD.S.6 | 1 | 1 | LIG.LISD.S.6 (1) |
| Polygon49 | LIG.LISD.S.7 | 4 | 2 | LIG.LISD.S.6 (2), LIG.LISD.S.7 (2) |
| Polygon50 | LIG.S.1 | 1 | 1 | LIG.S.1 (1) |
| Polygon51 | LIG.S.2 | 1 | 1 | LIG.S.2 (1) |
| Polygon52 | LIG.S.3 | 1 | 1 | LIG.S.3 (1) |
| Polygon53 | LIG.S.4 | 1 | 1 | LIG.S.4 (1) |
| Polygon54 | LIG.S.5 | 1 | 1 | LIG.S.5 (1) |
| Polygon55 | LIG.SDT.S.8 | 6 | 5 | ACTIVE.W.2 (1), LIG.LISD.S.6 (1), LIG.SDT.S.8 (1), SDT.ACTIVE.AUX.2 (2), SDT.W.3 (1) |
| Polygon56 | LIG.W.1 | 1 | 1 | LIG.W.1 (1) |
| Polygon57 | LISD.A.1 | 1 | 1 | LISD.A.1 (1) |
| Polygon58 | LISD.S.1 | 1 | 1 | LISD.S.1 (1) |
| Polygon59 | LISD.S.2 | 1 | 1 | LISD.S.2 (1) |
| Polygon60 | LISD.S.3 | 1 | 1 | LISD.S.3 (1) |
| Polygon61 | LISD.W.1 | 1 | 1 | LISD.W.1 (1) |
| Polygon62 | LVT.ACTIVE.EN.1 | 2 | 1 | LVT.ACTIVE.EN.1 (2) |
| Polygon63 | LVT.ACTIVE.EN.2 | 2 | 1 | LVT.ACTIVE.EN.2 (2) |
| Polygon64 | LVT.GATE.EX.1 | 5 | 4 | ACTIVE.W.2 (1), GATE.S.3 (1), LVT.ACTIVE.EN.2 (2), LVT.GATE.EX.1 (1) |
| Polygon65 | LVT.GATE.EX.2 | 5 | 5 | ACTIVE.W.2 (1), GATE.S.3 (1), LVT.ACTIVE.EN.1 (1), LVT.ACTIVE.EN.2 (1), LVT.GATE.EX.2 (1) |
| Polygon66 | LVT.W.1 | 3 | 2 | LVT.ACTIVE.EN.1 (2), LVT.W.1 (1) |
| Polygon67 | LVT.W.2 | 3 | 2 | LVT.ACTIVE.EN.2 (2), LVT.W.2 (1) |
| Polygon68 | M1.A.1 | 1 | 1 | M1.A.1 (1) |
| Polygon69 | M1.R.0 | 1 | 1 | M1.R.0 (1) |
| Polygon70 | M1.S.1 | 1 | 1 | M1.S.1 (1) |
| Polygon71 | M1.S.2 | 1 | 1 | M1.S.2 (1) |
| Polygon72 | M1.S.3 | 1 | 1 | M1.S.3 (1) |
| Polygon73 | M1.S.4 | 1 | 1 | M1.S.4 (1) |
| Polygon74 | M1.S.5 | 1 | 1 | M1.S.5 (1) |
| Polygon75 | M1.S.6 | 2 | 1 | M1.S.6 (2) |
| Polygon76 | M1.W.1 | 1 | 1 | M1.W.1 (1) |
| Polygon77 | M2.A.1 | 1 | 1 | M2.A.1 (1) |
| Polygon78 | M2.S.1 | 1 | 1 | M2.S.1 (1) |
| Polygon79 | M2.S.2 | 1 | 1 | M2.S.2 (1) |
| Polygon80 | M2.S.3 | 2 | 2 | M2.S.3 (1), M2.S.7 (1) |
| Polygon81 | M2.S.4 | 2 | 2 | M2.S.4 (1), M2.S.7 (1) |
| Polygon82 | M2.S.5 | 2 | 2 | M2.S.5 (1), M2.S.7 (1) |
| Polygon83 | M2.S.6 | 2 | 1 | M2.S.6 (2) |
| Polygon84 | M2.S.7 | 2 | 1 | M2.S.7 (2) |
| Polygon85 | M2.S.8 | 2 | 1 | M2.S.8 (2) |
| Polygon86 | M2.W.1 | 1 | 1 | M2.W.1 (1) |
| Polygon87 | M3.A.1 | 1 | 1 | M3.A.1 (1) |
| Polygon88 | M3.S.1 | 1 | 1 | M3.S.1 (1) |
| Polygon89 | M3.S.2 | 1 | 1 | M3.S.2 (1) |
| Polygon90 | M3.S.3 | 1 | 1 | M3.S.3 (1) |
| Polygon91 | M3.S.4 | 1 | 1 | M3.S.4 (1) |
| Polygon92 | M3.S.5 | 1 | 1 | M3.S.5 (1) |
| Polygon93 | M3.S.6 | 2 | 1 | M3.S.6 (2) |
| Polygon94 | M3.W.1 | 1 | 1 | M3.W.1 (1) |
| Polygon95 | M4.AUX.1 | 2 | 2 | M4.AUX.1 (1), M4.W.5 (1) |
| Polygon96 | M4.AUX.2 | 9 | 5 | M4.AUX.2 (1), M4.AUX.3 (4), M4.S.4 (2), M4.W.3 (1), M4.W.5 (1) |
| Polygon97 | M4.AUX.3 | 3 | 2 | M4.AUX.3 (2), M4.W.4 (1) |
| Polygon98 | M4.AUX.4 | 1 | 1 | M4.AUX.4 (1) |
| Polygon99 | M4.S.1 | 2 | 2 | M4.AUX.1 (1), M4.S.1 (1) |
| Polygon100 | M4.S.2 | 3 | 2 | M4.S.2 (1), M4.W.3 (2) |
| Polygon101 | M4.S.3 | 6 | 4 | M4.AUX.1 (1), M4.S.2 (1), M4.S.3 (2), M4.W.4 (2) |
| Polygon102 | M4.S.4 | 8 | 5 | M4.AUX.1 (2), M4.S.2 (1), M4.S.3 (2), M4.S.4 (2), M4.S.5 (1) |
| Polygon103 | M4.S.5 | 5 | 3 | M4.AUX.1 (2), M4.S.4 (2), M4.S.5 (1) |
| Polygon104 | M4.W.1 | 2 | 2 | M4.AUX.1 (1), M4.W.1 (1) |
| Polygon105 | M4.W.2 | 2 | 2 | M4.AUX.1 (1), M4.W.2 (1) |
| Polygon106 | M4.W.3 | 1 | 1 | M4.W.3 (1) |
| Polygon107 | M4.W.4 | 1 | 1 | M4.W.4 (1) |
| Polygon108 | M4.W.5 | 1 | 1 | M4.W.5 (1) |
| Polygon109 | M5.AUX.1 | 2 | 2 | M5.AUX.1 (1), M5.W.5 (1) |
| Polygon110 | M5.AUX.2 | 9 | 5 | M5.AUX.2 (1), M5.AUX.3 (4), M5.S.4 (2), M5.W.3 (1), M5.W.5 (1) |
| Polygon111 | M5.AUX.3 | 4 | 3 | M5.AUX.3 (2), M5.W.3 (1), M5.W.4 (1) |
| Polygon112 | M5.AUX.4 | 1 | 1 | M5.AUX.4 (1) |
| Polygon113 | M5.S.1 | 2 | 2 | M5.AUX.1 (1), M5.S.1 (1) |
| Polygon114 | M5.S.2 | 3 | 2 | M5.S.2 (1), M5.W.3 (2) |
| Polygon115 | M5.S.3 | 6 | 4 | M5.AUX.1 (1), M5.S.2 (1), M5.S.3 (2), M5.W.4 (2) |
| Polygon116 | M5.S.4 | 2 | 1 | M5.S.4 (2) |
| Polygon117 | M5.S.5 | 5 | 3 | M5.AUX.1 (2), M5.S.4 (2), M5.S.5 (1) |
| Polygon118 | M5.W.1 | 2 | 2 | M5.AUX.1 (1), M5.W.1 (1) |
| Polygon119 | M5.W.2 | 2 | 2 | M5.AUX.1 (1), M5.W.2 (1) |
| Polygon120 | M5.W.3 | 1 | 1 | M5.W.3 (1) |
| Polygon121 | M5.W.4 | 1 | 1 | M5.W.4 (1) |
| Polygon122 | M5.W.5 | 1 | 1 | M5.W.5 (1) |
| Polygon123 | M6.AUX.1 | 1 | 1 | M6.AUX.1 (1) |
| Polygon124 | M6.AUX.2 | 1 | 1 | M6.AUX.2 (1) |
| Polygon125 | M6.AUX.3 | 3 | 2 | M6.AUX.3 (2), M6.W.4 (1) |
| Polygon126 | M6.AUX.4 | 2 | 1 | M6.AUX.4 (2) |
| Polygon127 | M6.S.1 | 2 | 2 | M6.AUX.1 (1), M6.S.1 (1) |
| Polygon128 | M6.S.2 | 3 | 2 | M6.S.2 (1), M6.W.3 (2) |
| Polygon129 | M6.S.3 | 6 | 4 | M6.AUX.1 (1), M6.S.2 (1), M6.S.3 (2), M6.W.4 (2) |
| Polygon130 | M6.S.4 | 7 | 4 | M6.AUX.1 (2), M6.S.3 (2), M6.S.4 (2), M6.S.5 (1) |
| Polygon131 | M6.S.5 | 10 | 4 | M6.AUX.1 (4), M6.S.1 (1), M6.S.4 (4), M6.S.5 (1) |
| Polygon132 | M6.W.1 | 2 | 2 | M6.AUX.1 (1), M6.W.1 (1) |
| Polygon133 | M6.W.2 | 2 | 2 | M6.AUX.1 (1), M6.W.2 (1) |
| Polygon134 | M6.W.3 | 1 | 1 | M6.W.3 (1) |
| Polygon135 | M6.W.4 | 1 | 1 | M6.W.4 (1) |
| Polygon136 | M6.W.5 | 1 | 1 | M6.W.5 (1) |
| Polygon137 | M7.AUX.1 | 1 | 1 | M7.AUX.1 (1) |
| Polygon138 | M7.AUX.2 | 1 | 1 | M7.AUX.2 (1) |
| Polygon139 | M7.AUX.3 | 4 | 3 | M7.AUX.3 (2), M7.W.3 (1), M7.W.4 (1) |
| Polygon140 | M7.AUX.4 | 2 | 1 | M7.AUX.4 (2) |
| Polygon141 | M7.S.1 | 2 | 2 | M7.AUX.1 (1), M7.S.1 (1) |
| Polygon142 | M7.S.2 | 3 | 2 | M7.S.2 (1), M7.W.3 (2) |
| Polygon143 | M7.S.3 | 6 | 4 | M7.AUX.1 (1), M7.S.2 (1), M7.S.3 (2), M7.W.4 (2) |
| Polygon144 | M7.S.4 | 2 | 1 | M7.S.4 (2) |
| Polygon145 | M7.S.5 | 10 | 4 | M7.AUX.1 (4), M7.S.1 (1), M7.S.4 (4), M7.S.5 (1) |
| Polygon146 | M7.W.1 | 2 | 2 | M7.AUX.1 (1), M7.W.1 (1) |
| Polygon147 | M7.W.2 | 2 | 2 | M7.AUX.1 (1), M7.W.2 (1) |
| Polygon148 | M7.W.3 | 1 | 1 | M7.W.3 (1) |
| Polygon149 | M7.W.4 | 1 | 1 | M7.W.4 (1) |
| Polygon150 | M7.W.5 | 1 | 1 | M7.W.5 (1) |
| Polygon151 | M8.A.1 | 1 | 1 | M8.A.1 (1) |
| Polygon152 | M8.L.1 | 2 | 1 | M8.L.1 (2) |
| Polygon153 | M8.S.1 | 2 | 2 | M8.S.1 (1), M8.S.5 (1) |
| Polygon154 | M8.S.2 | 1 | 1 | M8.S.2 (1) |
| Polygon155 | M8.S.3 | 2 | 2 | M8.S.3 (1), M8.S.4 (1) |
| Polygon156 | M8.S.4 | 1 | 1 | M8.S.4 (1) |
| Polygon157 | M8.S.5 | 1 | 1 | M8.S.5 (1) |
| Polygon158 | M8.S.6 | 1 | 1 | M8.S.6 (1) |
| Polygon159 | M8.S.7 | 1 | 1 | M8.S.7 (1) |
| Polygon160 | M8.S.8 | 1 | 1 | M8.S.8 (1) |
| Polygon161 | M8.W.1 | 10 | 2 | M8.W.1 (1), M8.W.4 (9) |
| Polygon162 | M8.W.2 | 1 | 1 | M8.W.2 (1) |
| Polygon163 | M8.W.3 | 3 | 3 | M8.W.3 (1), M8.W.4 (1), M8.W.5 (1) |
| Polygon164 | M8.W.4 | 2 | 2 | M8.W.4 (1), M8.W.5 (1) |
| Polygon165 | M8.W.5 | 1 | 1 | M8.W.5 (1) |
| Polygon166 | M9.A.1 | 1 | 1 | M9.A.1 (1) |
| Polygon167 | M9.L.1 | 2 | 1 | M9.L.1 (2) |
| Polygon168 | M9.S.1 | 3 | 2 | M9.A.1 (2), M9.S.1 (1) |
| Polygon169 | M9.S.2 | 1 | 1 | M9.S.2 (1) |
| Polygon170 | M9.S.3 | 2 | 2 | M9.S.3 (1), M9.S.4 (1) |
| Polygon171 | M9.S.4 | 1 | 1 | M9.S.4 (1) |
| Polygon172 | M9.S.5 | 1 | 1 | M9.S.5 (1) |
| Polygon173 | M9.S.6 | 1 | 1 | M9.S.6 (1) |
| Polygon174 | M9.S.7 | 1 | 1 | M9.S.7 (1) |
| Polygon175 | M9.S.8 | 1 | 1 | M9.S.8 (1) |
| Polygon176 | M9.W.1 | 2 | 2 | M9.A.1 (1), M9.W.1 (1) |
| Polygon177 | M9.W.2 | 1 | 1 | M9.W.2 (1) |
| Polygon178 | M9.W.3 | 1 | 1 | M9.W.3 (1) |
| Polygon179 | M9.W.4 | 1 | 1 | M9.W.4 (1) |
| Polygon180 | M9.W.5 | 1 | 1 | M9.W.5 (1) |
| Polygon181 | NSELECT.ACTIVE.EN.1 | 2 | 1 | NSELECT.ACTIVE.EN.1 (2) |
| Polygon182 | NSELECT.ACTIVE.EN.2 | 2 | 1 | NSELECT.ACTIVE.EN.2 (2) |
| Polygon183 | NSELECT.GATE.EX.1 | 4 | 4 | ACTIVE.AUX.1 (1), ACTIVE.W.2 (1), GATE.S.3 (1), NSELECT.GATE.EX.1 (1) |
| Polygon184 | NSELECT.GATE.EX.2 | 5 | 5 | ACTIVE.W.2 (1), GATE.S.3 (1), NSELECT.ACTIVE.EN.1 (1), NSELECT.ACTIVE.EN.2 (1), NSELECT.GATE.EX.2 (1) |
| Polygon185 | NSELECT.PSELECT.AUX.1 | 1 | 1 | NSELECT.PSELECT.AUX.1 (1) |
| Polygon186 | NSELECT.W.1 | 3 | 2 | NSELECT.ACTIVE.EN.1 (2), NSELECT.W.1 (1) |
| Polygon187 | NSELECT.W.2 | 3 | 2 | NSELECT.ACTIVE.EN.2 (2), NSELECT.W.2 (1) |
| Polygon188 | PSELECT.ACTIVE.EN.1 | 2 | 1 | PSELECT.ACTIVE.EN.1 (2) |
| Polygon189 | PSELECT.ACTIVE.EN.2 | 2 | 1 | PSELECT.ACTIVE.EN.2 (2) |
| Polygon190 | PSELECT.GATE.EX.1 | 9 | 7 | ACTIVE.AUX.1 (1), ACTIVE.LUP.1 (1), ACTIVE.W.2 (1), ACTIVE.WELL.EN.1 (3), GATE.S.3 (1), PSELECT.GATE.EX.1 (1), WELL.GATE.EX.2 (1) |
| Polygon191 | PSELECT.GATE.EX.2 | 6 | 6 | ACTIVE.LUP.1 (1), ACTIVE.W.2 (1), GATE.S.3 (1), PSELECT.ACTIVE.EN.1 (1), PSELECT.ACTIVE.EN.2 (1), PSELECT.GATE.EX.2 (1) |
| Polygon192 | PSELECT.W.1 | 3 | 2 | PSELECT.ACTIVE.EN.1 (2), PSELECT.W.1 (1) |
| Polygon193 | PSELECT.W.2 | 3 | 2 | PSELECT.ACTIVE.EN.2 (2), PSELECT.W.2 (1) |
| Polygon194 | SDT.ACTIVE.AUX.2 | 3 | 2 | SDT.ACTIVE.AUX.2 (2), SDT.W.3 (1) |
| Polygon195 | SDT.ACTIVE.AUX.3 | 1 | 1 | SDT.ACTIVE.AUX.3 (1) |
| Polygon196 | SDT.ACTIVE.OV.1 | 2 | 2 | SDT.ACTIVE.AUX.2 (1), SDT.ACTIVE.OV.1 (1) |
| Polygon197 | SDT.GATE.AUX.1 | 6 | 6 | ACTIVE.W.2 (1), GATE.ACTIVE.AUX.3 (1), GATE.S.3 (1), SDT.GATE.AUX.1 (1), SDT.LISD.AUX.4 (1), SDT.W.3 (1) |
| Polygon198 | SDT.GATE.S.2 | 6 | 6 | ACTIVE.W.2 (1), GATE.ACTIVE.S.4 (1), GATE.S.3 (1), SDT.GATE.S.2 (1), SDT.LISD.AUX.4 (1), SDT.W.3 (1) |
| Polygon199 | SDT.LISD.AUX.4 | 1 | 1 | SDT.LISD.AUX.4 (1) |
| Polygon200 | SDT.LISD.OV.2 | 2 | 2 | SDT.LISD.AUX.4 (1), SDT.LISD.OV.2 (1) |
| Polygon201 | SDT.S.1 | 1 | 1 | SDT.S.1 (1) |
| Polygon202 | SDT.W.1 | 1 | 1 | SDT.W.1 (1) |
| Polygon203 | SDT.W.2 | 4 | 4 | ACTIVE.W.1 (1), ACTIVE.W.2 (1), LISD.W.1 (1), SDT.W.2 (1) |
| Polygon204 | SDT.W.3 | 2 | 2 | ACTIVE.W.2 (1), SDT.W.3 (1) |
| Polygon205 | SLVT.ACTIVE.EN.1 | 2 | 1 | SLVT.ACTIVE.EN.1 (2) |
| Polygon206 | SLVT.ACTIVE.EN.2 | 2 | 1 | SLVT.ACTIVE.EN.2 (2) |
| Polygon207 | SLVT.GATE.EX.1 | 5 | 4 | ACTIVE.W.2 (1), GATE.S.3 (1), SLVT.ACTIVE.EN.2 (2), SLVT.GATE.EX.1 (1) |
| Polygon208 | SLVT.GATE.EX.2 | 5 | 5 | ACTIVE.W.2 (1), GATE.S.3 (1), SLVT.ACTIVE.EN.1 (1), SLVT.ACTIVE.EN.2 (1), SLVT.GATE.EX.2 (1) |
| Polygon209 | SLVT.W.1 | 3 | 2 | SLVT.ACTIVE.EN.1 (2), SLVT.W.1 (1) |
| Polygon210 | SLVT.W.2 | 3 | 2 | SLVT.ACTIVE.EN.2 (2), SLVT.W.2 (1) |
| Polygon211 | SRAM.ACTIVE.A.2A | 2 | 2 | ACTIVE.W.3 (1), SRAM.ACTIVE.A.2A (1) |
| Polygon212 | SRAM.ACTIVE.A.2B | 6 | 4 | ACTIVE.AUX.3 (1), ACTIVE.S.2B (1), ACTIVE.W.2 (3), SRAM.ACTIVE.A.2B (1) |
| Polygon213 | SRAM.ACTIVE.AUX.2 | 1 | 1 | SRAM.ACTIVE.AUX.2 (1) |
| Polygon214 | SRAM.ACTIVE.WELL.EN.2 | 4 | 3 | ACTIVE.LUP.1 (1), ACTIVE.W.2 (1), SRAM.ACTIVE.WELL.EN.2 (2) |
| Polygon215 | SRAM.ACTIVE.WELL.S.5 | 1 | 1 | SRAM.ACTIVE.WELL.S.5 (1) |
| Polygon216 | SRAM.LIG.AUX.2 | 1 | 1 | SRAM.LIG.AUX.2 (1) |
| Polygon217 | SRAM.LIG.GATE.A.4 | 3 | 3 | LIG.A.1 (1), LIG.W.1 (1), SRAM.LIG.GATE.A.4 (1) |
| Polygon218 | SRAM.LIG.GATE.OV.2 | 4 | 4 | LIG.A.1 (1), LIG.W.1 (1), SRAM.LIG.GATE.A.4 (1), SRAM.LIG.GATE.OV.2 (1) |
| Polygon219 | SRAM.LISD.AUX.1 | 1 | 1 | SRAM.LISD.AUX.1 (1) |
| Polygon220 | SRAM.LISD.S.4 | 1 | 1 | SRAM.LISD.S.4 (1) |
| Polygon221 | SRAM.LVT.ACTIVE.EN.3 | 3 | 2 | LVT.W.1 (1), SRAM.LVT.ACTIVE.EN.3 (2) |
| Polygon222 | SRAM.LVT.ACTIVE.EN.4 | 4 | 3 | LVT.W.1 (1), LVT.W.2 (1), SRAM.LVT.ACTIVE.EN.4 (2) |
| Polygon223 | SRAM.NSELECT.ACTIVE.EN.3 | 3 | 2 | NSELECT.W.1 (1), SRAM.NSELECT.ACTIVE.EN.3 (2) |
| Polygon224 | SRAM.NSELECT.ACTIVE.EN.4 | 4 | 3 | NSELECT.W.1 (1), NSELECT.W.2 (1), SRAM.NSELECT.ACTIVE.EN.4 (2) |
| Polygon225 | SRAM.PSELECT.ACTIVE.EN.3 | 3 | 2 | PSELECT.W.1 (1), SRAM.PSELECT.ACTIVE.EN.3 (2) |
| Polygon226 | SRAM.PSELECT.ACTIVE.EN.4 | 4 | 3 | PSELECT.W.1 (1), PSELECT.W.2 (1), SRAM.PSELECT.ACTIVE.EN.4 (2) |
| Polygon227 | SRAM.SDT.ACTIVE.OV.3 | 4 | 4 | LISD.A.1 (1), LISD.W.1 (1), SRAM.SDT.ACTIVE.OV.3 (1), SRAM.SDT.W.4 (1) |
| Polygon228 | SRAM.SDT.LISD.OV.4 | 2 | 2 | SDT.LISD.AUX.4 (1), SRAM.SDT.LISD.OV.4 (1) |
| Polygon229 | SRAM.SDT.W.4 | 4 | 4 | ACTIVE.W.1 (1), ACTIVE.W.2 (1), LISD.W.1 (1), SRAM.SDT.W.4 (1) |
| Polygon230 | SRAM.SLVT.ACTIVE.EN.3 | 3 | 2 | SLVT.W.1 (1), SRAM.SLVT.ACTIVE.EN.3 (2) |
| Polygon231 | SRAM.SLVT.ACTIVE.EN.4 | 4 | 3 | SLVT.W.1 (1), SLVT.W.2 (1), SRAM.SLVT.ACTIVE.EN.4 (2) |
| Polygon232 | SRAM.SRAMVT.ACTIVE.EN.3 | 3 | 2 | SRAM.SRAMVT.ACTIVE.EN.3 (2), SRAMVT.W.1 (1) |
| Polygon233 | SRAM.SRAMVT.ACTIVE.EN.4 | 4 | 3 | SRAM.SRAMVT.ACTIVE.EN.4 (2), SRAMVT.W.1 (1), SRAMVT.W.2 (1) |
| Polygon234 | SRAMVT.ACTIVE.EN.1 | 2 | 1 | SRAMVT.ACTIVE.EN.1 (2) |
| Polygon235 | SRAMVT.ACTIVE.EN.2 | 2 | 1 | SRAMVT.ACTIVE.EN.2 (2) |
| Polygon236 | SRAMVT.GATE.EX.1 | 5 | 4 | ACTIVE.W.2 (1), GATE.S.3 (1), SRAMVT.ACTIVE.EN.2 (2), SRAMVT.GATE.EX.1 (1) |
| Polygon237 | SRAMVT.GATE.EX.2 | 5 | 5 | ACTIVE.W.2 (1), GATE.S.3 (1), SRAMVT.ACTIVE.EN.1 (1), SRAMVT.ACTIVE.EN.2 (1), SRAMVT.GATE.EX.2 (1) |
| Polygon238 | SRAMVT.W.1 | 3 | 2 | SRAMVT.ACTIVE.EN.1 (2), SRAMVT.W.1 (1) |
| Polygon239 | SRAMVT.W.2 | 3 | 2 | SRAMVT.ACTIVE.EN.2 (2), SRAMVT.W.2 (1) |
| Polygon240 | V0.AUX.1 | 3 | 3 | V0.AUX.1 (1), V0.M1.AUX.3 (1), V0.M1.EN.1 (1) |
| Polygon241 | V0.LIG.A.1 | 3 | 3 | V0.LIG.A.1 (1), V0.LIG.AUX.2 (1), V0.M1.AUX.3 (1) |
| Polygon242 | V0.LIG.AUX.2 | 3 | 3 | V0.LIG.A.1 (1), V0.LIG.AUX.2 (1), V0.M1.AUX.3 (1) |
| Polygon243 | V0.LIG.EN.4 | 5 | 2 | V0.LIG.EN.4 (4), V0.M1.AUX.3 (1) |
| Polygon244 | V0.LISD.EN.2 | 2 | 2 | V0.LISD.EN.2 (1), V0.M1.AUX.3 (1) |
| Polygon245 | V0.LISD.EN.3 | 2 | 2 | V0.LISD.EN.3 (1), V0.M1.AUX.3 (1) |
| Polygon246 | V0.M1.AUX.3 | 1 | 1 | V0.M1.AUX.3 (1) |
| Polygon247 | V0.M1.EN.1 | 6 | 2 | V0.M1.AUX.3 (1), V0.M1.EN.1 (5) |
| Polygon248 | V0.S.1 | 17 | 4 | M1.A.1 (6), M1.S.4 (3), V0.M1.EN.1 (6), V0.S.1 (2) |
| Polygon249 | V0.S.2 | 42 | 5 | M1.A.1 (2), M1.S.6 (6), M1.W.1 (24), V0.M1.EN.1 (2), V0.S.2 (8) |
| Polygon250 | V0.S.3 | 6 | 3 | M1.A.1 (2), V0.M1.EN.1 (2), V0.S.3 (2) |
| Polygon251 | V0.S.4 | 22 | 5 | M1.A.1 (2), M1.S.6 (2), M1.W.1 (12), V0.M1.EN.1 (2), V0.S.4 (4) |
| Polygon252 | V0.W.1 | 2 | 2 | V0.M1.AUX.3 (1), V0.W.1 (1) |
| Polygon253 | V1.AUX.1 | 3 | 3 | V1.AUX.1 (1), V1.M1.EN.1 (1), V1.M2.AUX.2 (1) |
| Polygon254 | V1.M1.EN.1 | 2 | 2 | M1.A.1 (1), V1.M1.EN.1 (1) |
| Polygon255 | V1.M2.AUX.2 | 1 | 1 | V1.M2.AUX.2 (1) |
| Polygon256 | V1.M2.EN.2 | 6 | 2 | V1.M2.AUX.2 (1), V1.M2.EN.2 (5) |
| Polygon257 | V1.S.1 | 18 | 5 | M2.A.1 (6), M2.S.4 (3), M2.S.7 (1), V1.M2.EN.2 (6), V1.S.1 (2) |
| Polygon258 | V1.S.2 | 46 | 7 | M2.A.1 (2), M2.S.6 (6), M2.W.1 (24), V1.AUX.1 (2), V1.M1.EN.1 (2), V1.M2.EN.2 (2), V1.S.2 (8) |
| Polygon259 | V1.S.3 | 6 | 3 | M2.A.1 (2), V1.M2.EN.2 (2), V1.S.3 (2) |
| Polygon260 | V1.S.4 | 26 | 7 | M2.A.1 (2), M2.S.6 (2), M2.W.1 (12), V1.AUX.1 (2), V1.M1.EN.1 (2), V1.M2.EN.2 (2), V1.S.4 (4) |
| Polygon261 | V1.W.1 | 2 | 2 | V1.M2.AUX.2 (1), V1.W.1 (1) |
| Polygon262 | V2.AUX.1 | 3 | 3 | V2.AUX.1 (1), V2.M2.EN.1 (1), V2.M3.AUX.2 (1) |
| Polygon263 | V2.M2.EN.1 | 2 | 2 | V2.M2.EN.1 (1), V2.M3.AUX.2 (1) |
| Polygon264 | V2.M3.AUX.2 | 1 | 1 | V2.M3.AUX.2 (1) |
| Polygon265 | V2.M3.EN.2 | 6 | 2 | V2.M3.AUX.2 (1), V2.M3.EN.2 (5) |
| Polygon266 | V2.S.1 | 17 | 4 | M3.A.1 (6), M3.S.4 (3), V2.M3.EN.2 (6), V2.S.1 (2) |
| Polygon267 | V2.S.2 | 46 | 7 | M3.A.1 (2), M3.S.6 (6), M3.W.1 (24), V2.AUX.1 (2), V2.M2.EN.1 (2), V2.M3.EN.2 (2), V2.S.2 (8) |
| Polygon268 | V2.S.3 | 6 | 3 | M3.A.1 (2), V2.M3.EN.2 (2), V2.S.3 (2) |
| Polygon269 | V2.S.4 | 26 | 7 | M3.A.1 (2), M3.S.6 (2), M3.W.1 (12), V2.AUX.1 (2), V2.M2.EN.1 (2), V2.M3.EN.2 (2), V2.S.4 (4) |
| Polygon270 | V2.W.1 | 2 | 2 | V2.M3.AUX.2 (1), V2.W.1 (1) |
| Polygon271 | V3.AUX.1 | 4 | 4 | M4.AUX.1 (1), V3.AUX.1 (1), V3.M3.EN.1 (1), V3.M4.AUX.2 (1) |
| Polygon272 | V3.M3.EN.1 | 3 | 3 | M4.AUX.1 (1), V3.M3.EN.1 (1), V3.M4.AUX.2 (1) |
| Polygon273 | V3.M4.AUX.2 | 2 | 2 | M4.AUX.1 (1), V3.M4.AUX.2 (1) |
| Polygon274 | V3.M4.EN.2 | 3 | 3 | M4.AUX.1 (1), V3.M4.AUX.2 (1), V3.M4.EN.2 (1) |
| Polygon275 | V3.S.1 | 37 | 9 | M4.AUX.1 (6), M4.S.1 (1), M4.S.2 (2), M4.S.3 (4), M4.S.4 (4), M4.W.1 (6), M4.W.5 (6), V3.M4.EN.2 (6), V3.S.1 (2) |
| Polygon276 | V3.S.2 | 244 | 12 | M4.AUX.1 (2), M4.AUX.3 (32), M4.S.1 (7), M4.S.2 (21), M4.S.3 (24), M4.S.4 (46), M4.W.1 (48), M4.W.5 (50), V3.AUX.1 (2), V3.M3.EN.1 (2), V3.M4.EN.2 (2), V3.S.2 (8) |
| Polygon277 | V3.S.3 | 16 | 9 | M4.AUX.1 (2), M4.S.1 (1), M4.S.2 (1), M4.S.3 (2), M4.S.4 (2), M4.W.1 (2), M4.W.5 (2), V3.M4.EN.2 (2), V3.S.3 (2) |
| Polygon278 | V3.S.4 | 113 | 12 | M4.AUX.1 (2), M4.AUX.3 (16), M4.S.1 (3), M4.S.2 (5), M4.S.3 (7), M4.S.4 (19), M4.W.1 (25), M4.W.5 (26), V3.AUX.1 (2), V3.M3.EN.1 (2), V3.M4.EN.2 (2), V3.S.4 (4) |
| Polygon279 | V3.W.1 | 3 | 3 | M4.AUX.1 (1), V3.M4.AUX.2 (1), V3.W.1 (1) |
| Polygon280 | V4.AUX.1 | 5 | 5 | M4.AUX.1 (1), M4.W.5 (1), M5.AUX.1 (1), V4.AUX.1 (1), V4.M5.AUX.2 (1) |
| Polygon281 | V4.M4.EN.1 | 4 | 4 | M4.AUX.1 (1), M5.AUX.1 (1), V4.M4.EN.1 (1), V4.M5.AUX.2 (1) |
| Polygon282 | V4.M5.AUX.2 | 3 | 3 | M4.AUX.1 (1), M5.AUX.1 (1), V4.M5.AUX.2 (1) |
| Polygon283 | V4.M5.EN.2 | 4 | 4 | M4.AUX.1 (1), M5.AUX.1 (1), V4.M5.AUX.2 (1), V4.M5.EN.2 (1) |
| Polygon284 | V4.S.1 | 5 | 4 | M4.AUX.1 (1), M5.AUX.1 (1), V4.M5.AUX.2 (2), V4.S.1 (1) |
| Polygon285 | V4.S.2 | 9 | 6 | M4.AUX.1 (2), M4.S.2 (1), M5.AUX.1 (2), M5.S.1 (1), V4.M5.AUX.2 (2), V4.S.2 (1) |
| Polygon286 | V4.S.3 | 6 | 4 | M4.AUX.1 (1), M5.AUX.1 (1), V4.M5.AUX.2 (2), V4.S.3 (2) |
| Polygon287 | V4.W.1 | 5 | 4 | M4.AUX.1 (1), M5.AUX.1 (1), V4.M5.AUX.2 (1), V4.W.1 (2) |
| Polygon288 | V5.AUX.1 | 5 | 5 | M5.AUX.1 (1), M6.AUX.1 (1), M6.W.1 (1), V5.AUX.1 (1), V5.M6.AUX.2 (1) |
| Polygon289 | V5.M5.EN.1 | 4 | 4 | M5.AUX.1 (1), M6.AUX.1 (1), V5.M5.EN.1 (1), V5.M6.AUX.2 (1) |
| Polygon290 | V5.M6.AUX.2 | 3 | 3 | M5.AUX.1 (1), M6.AUX.1 (1), V5.M6.AUX.2 (1) |
| Polygon291 | V5.M6.EN.2 | 4 | 4 | M5.AUX.1 (1), M6.AUX.1 (1), V5.M6.AUX.2 (1), V5.M6.EN.2 (1) |
| Polygon292 | V5.S.1 | 5 | 4 | M5.AUX.1 (1), M6.AUX.1 (1), V5.M6.AUX.2 (2), V5.S.1 (1) |
| Polygon293 | V5.S.2 | 9 | 6 | M5.AUX.1 (2), M5.S.1 (1), M6.AUX.1 (2), M6.S.2 (1), V5.M6.AUX.2 (2), V5.S.2 (1) |
| Polygon294 | V5.S.3 | 6 | 4 | M5.AUX.1 (1), M6.AUX.1 (1), V5.M6.AUX.2 (2), V5.S.3 (2) |
| Polygon295 | V5.W.1 | 5 | 4 | M5.AUX.1 (1), M6.AUX.1 (1), V5.M6.AUX.2 (1), V5.W.1 (2) |
| Polygon296 | V6.AUX.1 | 4 | 4 | M6.AUX.1 (1), M7.AUX.1 (1), V6.AUX.1 (1), V6.M7.AUX.2 (1) |
| Polygon297 | V6.M6.EN.1 | 6 | 5 | M6.AUX.1 (1), M7.AUX.1 (1), V6.M6.EN.1 (1), V6.M7.AUX.2 (1), V6.W.1 (2) |
| Polygon298 | V6.M7.AUX.2 | 3 | 3 | M6.AUX.1 (1), M7.AUX.1 (1), V6.M7.AUX.2 (1) |
| Polygon299 | V6.M7.EN.2 | 6 | 5 | M6.AUX.1 (1), M7.AUX.1 (1), V6.M7.AUX.2 (1), V6.M7.EN.2 (1), V6.W.1 (2) |
| Polygon300 | V6.S.1 | 5 | 4 | M6.AUX.1 (1), M7.AUX.1 (1), V6.M7.AUX.2 (2), V6.S.1 (1) |
| Polygon301 | V6.S.2 | 13 | 7 | M6.AUX.1 (2), M6.S.2 (1), M7.AUX.1 (2), M7.S.1 (1), V6.M7.AUX.2 (2), V6.S.2 (1), V6.W.1 (4) |
| Polygon302 | V6.S.3 | 6 | 4 | M6.AUX.1 (1), M7.AUX.1 (1), V6.M7.AUX.2 (2), V6.S.3 (2) |
| Polygon303 | V6.W.1 | 5 | 4 | M6.AUX.1 (1), M7.AUX.1 (1), V6.M7.AUX.2 (1), V6.W.1 (2) |
| Polygon304 | V7.AUX.1 | 5 | 5 | M7.AUX.1 (1), M8.A.1 (1), M8.W.1 (1), V7.AUX.1 (1), V7.M8.AUX.2 (1) |
| Polygon305 | V7.M7.EN.1 | 5 | 4 | M7.AUX.1 (1), V7.M7.EN.1 (1), V7.M8.AUX.2 (1), V7.W.1 (2) |
| Polygon306 | V7.M8.AUX.2 | 3 | 3 | M7.AUX.1 (1), M8.A.1 (1), V7.M8.AUX.2 (1) |
| Polygon307 | V7.M8.EN.2 | 5 | 4 | M7.AUX.1 (1), V7.M8.AUX.2 (1), V7.M8.EN.2 (1), V7.W.1 (2) |
| Polygon308 | V7.S.1 | 4 | 3 | M7.AUX.1 (1), V7.M8.AUX.2 (2), V7.S.1 (1) |
| Polygon309 | V7.S.2 | 13 | 7 | M7.AUX.1 (2), M7.S.1 (1), M8.A.1 (2), M8.S.1 (1), V7.M8.AUX.2 (2), V7.S.2 (1), V7.W.1 (4) |
| Polygon310 | V7.S.3 | 5 | 3 | M7.AUX.1 (1), V7.M8.AUX.2 (2), V7.S.3 (2) |
| Polygon311 | V7.W.1 | 5 | 4 | M7.AUX.1 (1), M8.A.1 (1), V7.M8.AUX.2 (1), V7.W.1 (2) |
| Polygon312 | V8.AUX.1 | 3 | 3 | M8.A.1 (1), M9.A.1 (1), V8.AUX.1 (1) |
| Polygon313 | V8.M8.EN.1 | 1 | 1 | V8.M8.EN.1 (1) |
| Polygon314 | V8.M9.EN.2 | 1 | 1 | V8.M9.EN.2 (1) |
| Polygon315 | V8.S.1 | 1 | 1 | V8.S.1 (1) |
| Polygon316 | V8.S.2 | 4 | 2 | V8.S.1 (2), V8.S.2 (2) |
| Polygon317 | V8.W.1 | 1 | 1 | V8.W.1 (1) |
| Polygon318 | V9.AUX.1 | 2 | 2 | M9.A.1 (1), V9.AUX.1 (1) |
| Polygon319 | V9.M9.EN.1 | 1 | 1 | V9.M9.EN.1 (1) |
| Polygon320 | V9.PAD.EN.2 | 1 | 1 | V9.PAD.EN.2 (1) |
| Polygon321 | V9.S.1 | 1 | 1 | V9.S.1 (1) |
| Polygon322 | V9.S.2 | 4 | 2 | V9.S.1 (2), V9.S.2 (2) |
| Polygon323 | V9.W.1 | 1 | 1 | V9.W.1 (1) |
| Polygon324 | VT.AUX.2 | 1 | 1 | VT.AUX.2 (1) |
| Polygon325 | WELL.A.1A | 2 | 2 | WELL.A.1A (1), WELL.W.2 (1) |
| Polygon326 | WELL.A.1B | 3 | 3 | WELL.A.1B (1), WELL.S.2 (1), WELL.W.1 (1) |
| Polygon327 | WELL.GATE.EX.1 | 2 | 2 | GATE.S.3 (1), WELL.GATE.EX.1 (1) |
| Polygon328 | WELL.GATE.EX.2 | 2 | 2 | GATE.S.3 (1), WELL.GATE.EX.2 (1) |
| Polygon329 | WELL.S.1 | 1 | 1 | WELL.S.1 (1) |
| Polygon330 | WELL.S.2 | 1 | 1 | WELL.S.2 (1) |
| Polygon331 | WELL.W.1 | 1 | 1 | WELL.W.1 (1) |
| Polygon332 | WELL.W.2 | 1 | 1 | WELL.W.2 (1) |
