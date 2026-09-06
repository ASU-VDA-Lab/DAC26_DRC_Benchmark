# DRC Change Log v2

Update the block-level benchmarks to remove DRC-violating power grid via structures introduced by OpenROAD-flow-scripts. The following shows the DRC type coverage and DRC changes for each block-level design.

## Comparison Scope

## DRC Type Coverage

There are 49 M1-M5 DRC rule types that OpenROAD drt module does not support. The table below shows the coverage of these DRC rule types for each updated block-level design.

| Block | Benchmark Coverage | Updated Coverage | Difference |
|---|---|---:|---:|---:|
| Block1 | 22.45% (11/49) | 20.41% (10/49) | -2.04 pp |
| Block2 | 16.33% (8/49) | 10.20% (5/49) | -6.12 pp |
| Block3 | 16.33% (8/49) | 18.37% (9/49) | +2.04 pp |
| Block4 | 20.41% (10/49) | 20.41% (10/49) | 0.00 pp |
| Block5 | 18.37% (9/49) | 14.29% (7/49) | -4.08 pp |
| Block6 | 20.41% (10/49) | 16.33% (8/49) | -4.08 pp |
| Block7 | 26.53% (13/49) | 20.41% (10/49) | -6.12 pp |

## 49-Type Coverage Reference

The following table is the complete 49 DRC rule types that OpenROAD drt module does not support.

| DRC Type | Description |
|---|---|
| `M1.R.0` | Redundant M1 island (approximation). M1 enclosing exactly one small V0 via is flagged near a large empty M1 region (>= 500 nm wide, area > 2.5 um-sq, expanded by 400 nm). |
| `M1.S.2` | Minimum (tip-to-side) spacing between two M1 layer polygons' edges, when one of the edges is <= 36 nm and the other is > 36 nm, is 25 nm. |
| `M1.S.3` | Minimum (tip-to-tip) spacing between two M1 layer polygons' edges, when both edges are >= 24 nm and <= 36 nm, is 27 nm. |
| `M1.S.4` | Minimum (tip-to-tip) spacing between two M1 layer polygons' edges, when both edges are < 24 nm, is 31 nm. |
| `M1.S.5` | Minimum (tip-to-tip) spacing between two M1 layer polygons' edges, when one of the edges is >= 24 nm and <= 36 nm, and the other is < 24 nm, is 31 nm. |
| `M1.S.6` | Minimum corner-to-corner spacing between two M1 polygons is 20 nm. |
| `V1.M1.EN.1` | Minimum enclosure of V1 by M1 on two opposite sides is 5 & 2 nm. |
| `V1.M2.AUX.2` | V1 must exactly be the same width as M2 along the direction perpendicular to the M2 length. |
| `V1.S.1` | Minimum spacing between V1 instances [on the same M2 track \| on parallel M2 tracks, not aligned \| on parallel M2 tracks, aligned] is [18 nm \| 27 nm \| 18 nm]. |
| `V1.S.2` | Minimum corner-to-corner spacing between two V1 instances--both with a 5 nm M2 end-cap--is 23 nm. |
| `V1.S.3` | Minimum corner-to-corner spacing between two V1 instances--both without a 5 nm M2 end-cap--is 30 nm. |
| `V1.S.4` | Minimum corner-to-corner spacing between two V1 instances--one with and another without, a 5 nm M2 end-cap--is 27 nm. |
| `M2.S.2` | Minimum (tip-to-side) spacing between two M2 layer polygons' edges, when one of the edges is <= 36 nm and the other is > 36 nm, is 25 nm. |
| `M2.S.3` | Minimum (tip-to-tip) spacing between two M2 layer polygons' edges, when both edges are >= 24 nm and <= 36 nm, is 27 nm. |
| `M2.S.5` | Minimum (tip-to-tip) spacing between two M2 layer polygons' edges, when one of the edges is >= 24 nm and <= 36 nm, and the other is < 24 nm, is 31 nm. |
| `M2.S.7` | M2 tip-to-tip (18 nm) co-located with side-to-side spacing <= 32 nm is forbidden; parallel run length must be >= 35 nm when side spacing <= 32 nm. |
| `M2.S.8` | Minimum diagonal center-to-center spacing between M2 tip-to-tip gaps on different tracks is 80 nm. Gap centers are found by shrinking each 18 nm tip-to-tip gap by 8.5 nm per side; euclidian distance between centers must be >= 80 nm. |
| `V2.M3.AUX.2` | V2 must exactly be the same width as M3 along the direction perpendicular to the M3 length. |
| `V2.S.1` | Minimum spacing between V2 instances [on the same M3 track \| on parallel M3 tracks, not aligned \| on parallel M3 tracks, aligned] is [18 nm \| 27 nm \| 18 nm]. |
| `V2.S.2` | Minimum corner-to-corner spacing between two V2 instances--both with a 5 nm M3 end-cap--is 23 nm. |
| `V2.S.3` | Minimum corner-to-corner spacing between two V2 instances--both without a 5 nm M3 end-cap--is 30 nm. |
| `V2.S.4` | Minimum corner-to-corner spacing between two V2 instances--one with and another without, a 5 nm M3 end-cap--is 27 nm. |
| `M3.S.2` | Minimum (tip-to-side) spacing between two M3 layer polygons' edges, when one of the edges is <= 36 nm and the other is > 36 nm, is 25 nm. |
| `M3.S.3` | Minimum (tip-to-tip) spacing between two M3 layer polygons' edges, when both edges are >= 24 nm and <= 36 nm, is 27 nm. |
| `M3.S.5` | Minimum (tip-to-tip) spacing between two M3 layer polygons' edges, when one of the edges is >= 24 nm and <= 36 nm, and the other is < 24 nm, is 31 nm. |
| `V3.M4.AUX.2` | V3 must exactly be the same width as M4 along the direction perpendicular to the M4 length. |
| `M4.AUX.1` | M4 horizontal edges must be at a grid of 24 nm. |
| `M4.AUX.2` | Minimum width M4 tracks must lie along the horizontal routing tracks at a spacing of 2N x minimum metal width + offset from the origin. |
| `M4.AUX.4` | Outside edge of a wide M4 layer polygon may not touch a routing track edge. |
| `M4.S.2` | Minimum horizontal spacing between two M4 layer polygons' edges, regardless of the edge lengths and mask colors, is 40 nm. |
| `M4.S.3` | Minimum tip-to-tip spacing between two M4 layer polygons--that do not share a parallel run length--on adjacent tracks is 40 nm. |
| `M4.S.4` | Minimum tip-to-tip spacing between two M4 layer polygons--that share a parallel run length--on adjacent tracks is 40 nm. |
| `M4.S.5` | Minimum parallel run length of two M4 layer polygons on adjacent tracks is 44 nm. |
| `M4.W.2` | Maximum vertical width of M4 is 480 nm. |
| `M4.W.3` | M4 vertical width may not be an even integer multiple of its minimum width. |
| `M4.W.4` | M4 vertical width, resulting in the polygon spanning an even number of minimum width routing tracks vertically, is not allowed. |
| `M4.W.5` | Minimum horizontal width of M4 is 44 nm. |
| `V4.M5.AUX.2` | V4 must exactly be the same width as M5 along the direction perpendicular to the M5 length. |
| `M5.AUX.1` | M5 vertical edges must be at a grid of 24 nm. |
| `M5.AUX.2` | Minimum width M5 tracks must lie along the vertical routing tracks at a spacing of 2N x minimum metal width + offset from the origin. |
| `M5.AUX.4` | Outside edge of a wide M5 layer polygon may not touch a routing track edge. |
| `M5.S.2` | Minimum vertical spacing between two M5 layer polygons' edges, regardless of the edge lengths and mask colors, is 40 nm. |
| `M5.S.3` | Minimum tip-to-tip spacing between two M5 layer polygons--that do not share a parallel run length--on adjacent tracks is 40 nm. |
| `M5.S.4` | Minimum tip-to-tip spacing between two M5 layer polygons--that share a parallel run length--on adjacent tracks is 40 nm. |
| `M5.S.5` | Minimum parallel run length of two M5 layer polygons on adjacent tracks is 44 nm. |
| `M5.W.2` | Maximum horizontal width of M5 is 480 nm. |
| `M5.W.3` | M5 horizontal width may not be an even integer multiple of its minimum width. |
| `M5.W.4` | M5 horizontal width, resulting in the polygon spanning an even number of minimum width routing tracks horizontally, is not allowed. |
| `M5.W.5` | Minimum vertical width of M5 is 44 nm. |

## Block1

| DRC Rule | Benchmark | Updated | Difference | Status |
|---|---:|---:|---:|---|
| `M1.S.2` | 12 | 31 | +19 | Increased |
| `M1.S.4` | 2 | 0 | -2 | Removed |
| `M1.S.5` | 0 | 1 | +1 | Added |
| `M1.S.6` | 0 | 12 | +12 | Added |
| `M2.S.7` | 1 | 5 | +4 | Increased |
| `M3.S.2` | 2 | 0 | -2 | Removed |
| `M4.AUX.1` | 18 | 104 | +86 | Increased |
| `M4.AUX.2` | 2 | 0 | -2 | Removed |
| `M4.S.4` | 0 | 1 | +1 | Added |
| `M4.S.5` | 4 | 2 | -2 | Decreased |
| `M5.AUX.1` | 8 | 16 | +8 | Increased |
| `M6.AUX.1` | 3 | 0 | -3 | Removed |
| `V0.M1.AUX.3` | 37 | 25 | -12 | Decreased |
| `V1.M1.EN.1` | 11 | 30 | +19 | Increased |
| `V2.M3.AUX.2` | 72 | 0 | -72 | Removed |
| `V3.M4.AUX.2` | 0 | 26 | +26 | Added |
| `V4.M5.AUX.2` | 48 | 0 | -48 | Removed |
| `V5.M6.AUX.2` | 24 | 0 | -24 | Removed |

## Block2

| DRC Rule | Benchmark | Updated | Difference | Status |
|---|---:|---:|---:|---|
| `M1.S.2` | 2 | 4 | +2 | Increased |
| `M4.AUX.1` | 6 | 32 | +26 | Increased |
| `M4.AUX.2` | 1 | 0 | -1 | Removed |
| `M4.S.5` | 1 | 0 | -1 | Removed |
| `M5.AUX.1` | 4 | 8 | +4 | Increased |
| `V0.M1.AUX.3` | 12 | 7 | -5 | Decreased |
| `V1.M1.EN.1` | 2 | 8 | +6 | Increased |
| `V2.M3.AUX.2` | 24 | 0 | -24 | Removed |
| `V3.M4.AUX.2` | 0 | 8 | +8 | Added |
| `V4.M5.AUX.2` | 16 | 0 | -16 | Removed |

## Block3

| DRC Rule | Benchmark | Updated | Difference | Status |
|---|---:|---:|---:|---|
| `M1.S.2` | 5 | 17 | +12 | Increased |
| `M1.S.4` | 1 | 3 | +2 | Increased |
| `M1.S.5` | 0 | 2 | +2 | Added |
| `M1.S.6` | 0 | 10 | +10 | Added |
| `M2.S.7` | 0 | 2 | +2 | Added |
| `M4.AUX.1` | 6 | 40 | +34 | Increased |
| `M4.AUX.2` | 1 | 0 | -1 | Removed |
| `M5.AUX.1` | 4 | 8 | +4 | Increased |
| `V0.M1.AUX.3` | 21 | 25 | +4 | Increased |
| `V1.M1.EN.1` | 6 | 17 | +11 | Increased |
| `V2.M3.AUX.2` | 27 | 0 | -27 | Removed |
| `V3.M4.AUX.2` | 0 | 10 | +10 | Added |
| `V4.M5.AUX.2` | 18 | 0 | -18 | Removed |

## Block4

| DRC Rule | Benchmark | Updated | Difference | Status |
|---|---:|---:|---:|---|
| `M1.S.2` | 8 | 18 | +10 | Increased |
| `M1.S.4` | 0 | 2 | +2 | Added |
| `M1.S.5` | 0 | 2 | +2 | Added |
| `M1.S.6` | 0 | 8 | +8 | Added |
| `M2.S.7` | 0 | 3 | +3 | Added |
| `M3.S.2` | 1 | 0 | -1 | Removed |
| `M4.AUX.1` | 11 | 88 | +77 | Increased |
| `M4.AUX.2` | 2 | 0 | -2 | Removed |
| `M4.S.4` | 1 | 0 | -1 | Removed |
| `M4.S.5` | 2 | 2 | 0 | Unchanged |
| `M5.AUX.1` | 6 | 16 | +10 | Increased |
| `M6.AUX.1` | 1 | 0 | -1 | Removed |
| `V0.M1.AUX.3` | 20 | 24 | +4 | Increased |
| `V1.M1.EN.1` | 4 | 23 | +19 | Increased |
| `V2.M3.AUX.2` | 51 | 0 | -51 | Removed |
| `V3.M4.AUX.2` | 0 | 22 | +22 | Added |
| `V4.M5.AUX.2` | 34 | 0 | -34 | Removed |
| `V5.M6.AUX.2` | 6 | 0 | -6 | Removed |

## Block5

| DRC Rule | Benchmark | Updated | Difference | Status |
|---|---:|---:|---:|---|
| `M1.S.2` | 6 | 3 | -3 | Decreased |
| `M1.S.6` | 2 | 4 | +2 | Increased |
| `M3.S.2` | 1 | 0 | -1 | Removed |
| `M4.AUX.1` | 5 | 24 | +19 | Increased |
| `M4.AUX.2` | 1 | 0 | -1 | Removed |
| `M4.S.5` | 0 | 1 | +1 | Added |
| `M5.AUX.1` | 4 | 8 | +4 | Increased |
| `V0.M1.AUX.3` | 9 | 6 | -3 | Decreased |
| `V1.M1.EN.1` | 5 | 2 | -3 | Decreased |
| `V2.M3.AUX.2` | 21 | 0 | -21 | Removed |
| `V3.M4.AUX.2` | 0 | 6 | +6 | Added |
| `V4.M5.AUX.2` | 14 | 0 | -14 | Removed |

## Block6

| DRC Rule | Benchmark | Updated | Difference | Status |
|---|---:|---:|---:|---|
| `M1.S.2` | 12 | 12 | 0 | Unchanged |
| `M1.S.4` | 1 | 3 | +2 | Increased |
| `M1.S.6` | 4 | 8 | +4 | Increased |
| `M2.S.7` | 0 | 3 | +3 | Added |
| `M3.S.2` | 3 | 0 | -3 | Removed |
| `M4.AUX.1` | 18 | 96 | +78 | Increased |
| `M4.AUX.2` | 4 | 0 | -4 | Removed |
| `M5.AUX.1` | 8 | 16 | +8 | Increased |
| `M6.AUX.1` | 4 | 0 | -4 | Removed |
| `V0.M1.AUX.3` | 21 | 18 | -3 | Decreased |
| `V1.M1.EN.1` | 10 | 12 | +2 | Increased |
| `V2.M3.AUX.2` | 78 | 0 | -78 | Removed |
| `V3.M4.AUX.2` | 0 | 24 | +24 | Added |
| `V4.M5.AUX.2` | 52 | 0 | -52 | Removed |
| `V5.M6.AUX.2` | 32 | 0 | -32 | Removed |

## Block7

| DRC Rule | Benchmark | Updated | Difference | Status |
|---|---:|---:|---:|---|
| `M1.S.2` | 25 | 61 | +36 | Increased |
| `M1.S.4` | 21 | 12 | -9 | Decreased |
| `M1.S.5` | 14 | 8 | -6 | Decreased |
| `M1.S.6` | 34 | 58 | +24 | Increased |
| `M2.S.7` | 4 | 18 | +14 | Increased |
| `M3.S.2` | 15 | 0 | -15 | Removed |
| `M4.AUX.1` | 54 | 288 | +234 | Increased |
| `M4.AUX.2` | 9 | 0 | -9 | Removed |
| `M4.S.5` | 1 | 2 | +1 | Increased |
| `M5.AUX.1` | 12 | 24 | +12 | Increased |
| `M6.AUX.1` | 6 | 0 | -6 | Removed |
| `V0.M1.AUX.3` | 97 | 81 | -16 | Decreased |
| `V1.M1.EN.1` | 26 | 95 | +69 | Increased |
| `V2.M3.AUX.2` | 225 | 0 | -225 | Removed |
| `V3.M4.AUX.2` | 0 | 72 | +72 | Added |
| `V4.M5.AUX.2` | 150 | 0 | -150 | Removed |
| `V5.M6.AUX.2` | 72 | 0 | -72 | Removed |
