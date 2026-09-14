(* ::Package:: *)

(* ================================================================== *)
(* BlackboxNLP 2026 Reproducibility Challenge paper figures            *)
(* arXiv (post-review) revision, 2026-09-04.                           *)
(* Data: committed candle-mi grid JSONs, copied into ../data           *)
(* Run:  wolframscript -file scripts/make_figures.wl                   *)
(* Output: ../figures/fig_position_sweep.pdf, fig_strength.pdf,        *)
(*         fig_newline_horizon.pdf, fig_random_controls.pdf            *)
(* Revision notes: reviewers found the submitted figures too small.    *)
(* Panels are now laid out two per row (2 x 2 grids) with fonts sized  *)
(* for a ~0.5 print scale, so labels land at 7 pt or more on the page. *)
(* ================================================================== *)

baseDir = Quiet@Check[DirectoryName[$InputFileName], NotebookDirectory[]];
If[baseDir === "" || baseDir === $Failed, baseDir = Directory[]];
dataDir = FileNameJoin[{baseDir, "..", "data"}];
figDir  = FileNameJoin[{baseDir, "..", "figures"}];
If[!DirectoryQ[figDir], CreateDirectory[figDir]];

(* Okabe-Ito colourblind-safe palette *)
okBlue = RGBColor["#0072B2"];
okVerm = RGBColor["#D55E00"];
okTeal = RGBColor["#009E73"];
okPurp = RGBColor["#CC79A7"];
okOrange = RGBColor["#E69F00"];
okBlack = GrayLevel[0.1];

(* Font sizes chosen for panels printed at about half their nominal size. *)
fsToken = 13; fsTick = 12; fsTitle = 14; fsAxis = 13; fsNote = 13;

loadCell[file_] := Import[FileNameJoin[{dataDir, file}], "RawJSON"];
rowAt[d_, s_] := SelectFirst[d["sweep_grid"], #["strength"] == s &]["sweep"];
cleanToken[t_] := StringReplace[t, {"<|begin_of_text|>" -> "<bos>",
  "\n" -> "\\n", " " -> "\[ThinSpace]"}];

(* Token labels: Consolas; newline tokens in the same orange as their bars. *)
styledTokenLabels[tokens_] := MapIndexed[
  Style[cleanToken[#1], fsToken, FontFamily -> "Consolas",
    If[StringContainsQ[#1, "\n"], okVerm, GrayLevel[0]]] &,
  tokens
];

fmtP[p_] := If[p < 0.01, ScientificForm[p, 2], NumberForm[p, {4, 3}]];

(* ================================================================== *)
(* Figure 1: position sweeps (log scale), newline bars highlighted     *)
(* ================================================================== *)

sweepBars[sweep_] := Module[{probs, tokens, imax},
  probs = sweep[[All, "prob"]];
  tokens = sweep[[All, "token"]];
  imax = First@Ordering[probs, -1];
  MapIndexed[
    Style[#1, Which[
      First[#2] == imax, okBlue,
      StringContainsQ[tokens[[First[#2]]], "\n"], okVerm,
      True, GrayLevel[0.65]
    ]] &,
    probs
  ]
];

sweepPanel[d_, s_, title_] := Module[{sweep, imax, probs},
  sweep = rowAt[d, s];
  probs = sweep[[All, "prob"]];
  imax = First@Ordering[probs, -1];
  BarChart[sweepBars[sweep],
    ChartLabels -> Placed[
      styledTokenLabels[sweep[[All, "token"]]],
      Below, Rotate[#, Pi/4] &
    ],
    ScalingFunctions -> "Log",
    PlotLabel -> Style[title, fsTitle],
    FrameLabel -> {None, Style["P(\"" <> d["inject_word"] <> "\")", fsAxis]},
    Frame -> True,
    FrameTicksStyle -> fsTick,
    BarSpacing -> 0.15,
    ImageSize -> 520,
    AspectRatio -> 0.6,
    ImagePadding -> {{70, 10}, {95, 30}},
    PlotRangePadding -> {{Scaled[0.01], Scaled[0.01]}, {0, Scaled[0.08]}},
    GridLines -> {None, {{d["baseline_prob"],
        Directive[Dashed, GrayLevel[0.45]]}}},
    Epilog -> {
      Text[Style["baseline", fsNote, GrayLevel[0.35]],
        Scaled[{0.10, 0.10}]],
      Text[Style[Row[{"P = ", fmtP[probs[[imax]]]}], fsNote, okBlue],
        Scaled[{0.76, 0.94}]]
    }
  ]
];

gemma  = loadCell["gemma_426k_out_grid.json"];
llama  = loadCell["llama_524k_ee_grid.json"];
q06t   = loadCell["qwen3_06b_20k_teen_grid.json"];
q17t   = loadCell["qwen3_17b_20k_teen_grid.json"];
q06a16 = loadCell["qwen3_06b_16k_ation_grid_v2.json"];

fig1 = GraphicsGrid[{
    {sweepPanel[gemma, 25.,
      "Gemma 2 2B \[Times] mntss 426K  (\[Minus]out \[RightArrow] \[OpenCurlyDoubleQuote]around\[CloseCurlyDoubleQuote], s = 25)"],
     sweepPanel[llama, 25.,
      "Llama 3.2 1B \[Times] mntss 524K  (\[Minus]ee \[RightArrow] \[OpenCurlyDoubleQuote]that\[CloseCurlyDoubleQuote], s = 25)"]},
    {sweepPanel[q06a16, 25.,
      "Qwen3-0.6B \[Times] BlueLightAI 16K  (\[Minus]ation \[RightArrow] \[OpenCurlyDoubleQuote]myself\[CloseCurlyDoubleQuote], s = 25)"],
     sweepPanel[q06t, 1.,
      "Qwen3-0.6B \[Times] BlueLightAI 20K  (\[Minus]teen \[RightArrow] \[OpenCurlyDoubleQuote]duration\[CloseCurlyDoubleQuote], s = 1)"]}
  },
  ImageSize -> 1060, Spacings -> {10, 10}
];

Export[FileNameJoin[{figDir, "fig_position_sweep.pdf"}], fig1];
Print["Exported fig_position_sweep.pdf"];

(* ================================================================== *)
(* Figure 2: strength response, best ratio over baseline per strength  *)
(* ================================================================== *)

strengthCurve[d_] := Module[{rows},
  rows = d["sweep_grid"];
  Table[
    {r["strength"], Max[r["sweep"][[All, "prob"]]] / d["baseline_prob"]},
    {r, rows}
  ]
];

curves = {
  strengthCurve[gemma],
  strengthCurve[llama],
  strengthCurve[q06a16],
  strengthCurve[q06t],
  strengthCurve[q17t]
};

legend = {
  "Gemma 2 2B / 426K (\[Minus]out)",
  "Llama 3.2 1B / 524K (\[Minus]ee)",
  "Qwen3-0.6B / 16K (\[Minus]ation)",
  "Qwen3-0.6B / 20K (\[Minus]teen)",
  "Qwen3-1.7B / 20K (\[Minus]teen)"
};

fig2 = ListLogLogPlot[curves,
  Joined -> True,
  PlotMarkers -> {
    {"\[FilledCircle]", 11}, {"\[FilledSquare]", 11},
    {"\[FilledUpTriangle]", 12}, {"\[FilledDiamond]", 12},
    {"\[FilledDownTriangle]", 12}
  },
  PlotStyle -> {
    Directive[okBlue, AbsoluteThickness[1.8]],
    Directive[okVerm, AbsoluteThickness[1.8]],
    Directive[okTeal, AbsoluteThickness[1.8]],
    Directive[okPurp, AbsoluteThickness[1.8], Dashed],
    Directive[okBlack, AbsoluteThickness[1.8], Dashed]
  },
  PlotLegends -> Placed[
    LineLegend[Automatic, legend, LegendMarkerSize -> 18,
      LabelStyle -> 12],
    {0.24, 0.76}
  ],
  Frame -> True,
  FrameLabel -> {
    Style["steering strength s", 14],
    Style["best ratio over baseline", 14]
  },
  FrameTicksStyle -> 12,
  GridLines -> {None, {{1, Directive[Dashed, GrayLevel[0.45]]}}},
  ImageSize -> 420,
  AspectRatio -> 0.8,
  PlotRangePadding -> Scaled[0.05]
];

Export[FileNameJoin[{figDir, "fig_strength.pdf"}], fig2];
Print["Exported fig_strength.pdf"];

(* ================================================================== *)
(* Figure 3: composition-horizon sweep (Exp 2, m4).                    *)
(* Prompt ends at the line-3 newline; the model composes line 4.       *)
(* Bars: gray = prompt, lighter = composed line, vermillion = newline, *)
(* blue = max.                                                         *)
(* ================================================================== *)

horizonBars[m4_, nPrompt_, nlIdx_] := Module[{probs, imax},
  probs = m4[[All, "p_inject"]];
  imax = First@Ordering[probs, -1];
  MapIndexed[
    Style[#1, Which[
      First[#2] == imax, okBlue,
      First[#2] - 1 == nlIdx, okVerm,
      First[#2] - 1 >= nPrompt, GrayLevel[0.82],
      True, GrayLevel[0.6]
    ]] &,
    probs
  ]
];

horizonPanel[file_, title_] := Module[
  {d, m4, probs, imax, nPrompt, nlIdx},
  d = Import[FileNameJoin[{dataDir, file}], "RawJSON"];
  m4 = d["m4_position_sweep"];
  nPrompt = Length[d["tokens"]];
  nlIdx = d["newline_index"];
  probs = m4[[All, "p_inject"]];
  imax = First@Ordering[probs, -1];
  BarChart[horizonBars[m4, nPrompt, nlIdx],
    ChartLabels -> Placed[
      styledTokenLabels[m4[[All, "token"]]],
      Below, Rotate[#, Pi/4] &
    ],
    ScalingFunctions -> "Log",
    PlotLabel -> Style[title, fsTitle],
    FrameLabel -> {None,
      Style["P(\"" <> d["inject_word"] <> "\") at final-word slot", fsAxis]},
    Frame -> True,
    FrameTicksStyle -> fsTick,
    BarSpacing -> 0.15,
    ImageSize -> 520,
    AspectRatio -> 0.6,
    ImagePadding -> {{70, 10}, {95, 30}},
    PlotRangePadding -> {{Scaled[0.01], Scaled[0.01]}, {0, Scaled[0.08]}},
    Epilog -> {
      Text[Style["newline", fsNote, okVerm],
        Scaled[{(nlIdx + 0.5)/Length[m4], 0.80}]],
      {okVerm, Arrowheads[0.03],
        Arrow[{Scaled[{(nlIdx + 0.5)/Length[m4], 0.74}],
               Scaled[{(nlIdx + 0.5)/Length[m4], 0.22}]}]},
      Text[Style[Row[{"P = ", fmtP[probs[[imax]]]}], fsNote, okBlue],
        Scaled[{0.74, 0.94}]]
    }
  ]
];

fig3 = GraphicsGrid[{
    {horizonPanel["fullline_gemma2-2b-426k.json",
      "Gemma 2 2B \[Times] mntss 426K  (group-level, s = 25)"],
     horizonPanel["fullline_gemma2-2b-2.5m.json",
      "Gemma 2 2B \[Times] mntss 2.5M  (word-level, s = 10)"]},
    {horizonPanel["fullline_llama3.2-1b-524k.json",
      "Llama 3.2 1B \[Times] mntss 524K  (group-level, s = 25)"],
     horizonPanel["fullline_qwen3-0.6b-16k-ation.json",
      "Qwen3-0.6B \[Times] BlueLightAI 16K  (\[Minus]ation, s = 25)"]}
  },
  ImageSize -> 1060, Spacings -> {10, 10}
];

Export[FileNameJoin[{figDir, "fig_newline_horizon.pdf"}], fig3];
Print["Exported fig_newline_horizon.pdf"];

(* ================================================================== *)
(* Figure 4 (new, appendix): per-position random controls.             *)
(* For each of the three strong cells: the real inject feature's       *)
(* P(target) per position (blue), the ten layer-matched random CLT     *)
(* features' P(target) (gray) and P(own top token) (orange), and the   *)
(* ten norm-matched random directions' P(target) (gray, dashed).       *)
(* Newline positions are marked by vertical orange lines.              *)
(* ================================================================== *)

(* Same half-width print scale as Figures 1 and 2. *)
rfTitle = fsTitle; rfAxis = fsAxis; rfTick = fsTick; rfNote = fsNote;

randomPanel[file_, title_] := Module[
  {d, n, real, ri, rd, nl, realPts, riT, riO, rdT, lines, allY, ymin, ymax},
  d = Import[FileNameJoin[{dataDir, file}], "RawJSON"];
  n = Length[d["tokens"]];
  nl = Flatten@Position[d["tokens"], _String?(StringContainsQ[#, "\n"] &), {1}] - 1;
  real = d["real_inject"]["per_position"];
  ri = d["random_inject"];
  rd = d["random_direction"];
  realPts = Table[{p["position"], p["p_target"]}, {p, real}];
  riT = Table[Table[{p["position"], p["p_target"]}, {p, dr["per_position"]}], {dr, ri}];
  riO = Table[Table[{p["position"], p["p_own"]}, {p, dr["per_position"]}], {dr, ri}];
  rdT = Table[Table[{p["position"], p["p_target"]}, {p, dr["per_position"]}], {dr, rd}];
  allY = Select[Flatten[{realPts[[All, 2]], riT[[All, All, 2]], riO[[All, All, 2]], rdT[[All, All, 2]]}], # > 0 &];
  ymin = 10^Floor[Log10[Min[allY]]]; ymax = 2;
  ListLogPlot[
    Join[riT, rdT, riO, {realPts}],
    Joined -> True,
    PlotStyle -> Join[
      Table[Directive[GrayLevel[0.55], AbsoluteThickness[0.8]], {Length[riT]}],
      Table[Directive[GrayLevel[0.55], AbsoluteThickness[0.8], Dashed], {Length[rdT]}],
      Table[Directive[okOrange, AbsoluteThickness[0.8]], {Length[riO]}],
      {Directive[okBlue, AbsoluteThickness[2.4]]}
    ],
    PlotMarkers -> Join[Table[None, {Length[riT] + Length[rdT] + Length[riO]}], {{"\[FilledCircle]", 9}}],
    PlotRange -> {{-0.5, n - 0.5}, {ymin, ymax}},
    Frame -> True,
    FrameLabel -> {Style["steering position (token index)", rfAxis],
      Style["probability", rfAxis]},
    FrameTicksStyle -> rfTick,
    PlotLabel -> Style[title, rfTitle],
    GridLines -> {nl, {{d["baseline_prob"], Directive[Dashed, GrayLevel[0.45]]}}},
    GridLinesStyle -> Directive[okVerm, AbsoluteThickness[1.6]],
    ImageSize -> 520,
    AspectRatio -> 0.7,
    ImagePadding -> {{70, 10}, {45, 30}},
    Epilog -> {
      Text[Style["newlines", rfNote, okVerm], Scaled[{0.13, 0.94}]],
      Text[Style["real feature, P(target)", rfNote, okBlue], Scaled[{0.62, 0.94}]],
      Text[Style["random features, P(own token)", rfNote, okOrange], Scaled[{0.62, 0.87}]],
      Text[Style["random features / directions, P(target)", rfNote, GrayLevel[0.4]], Scaled[{0.62, 0.80}]]
    }
  ]
];

(* Fourth panel: the strength-response plot, restyled to the grid's scale. *)
strengthPanel = ListLogLogPlot[curves,
  Joined -> True,
  PlotMarkers -> {
    {"\[FilledCircle]", 12}, {"\[FilledSquare]", 12},
    {"\[FilledUpTriangle]", 13}, {"\[FilledDiamond]", 13},
    {"\[FilledDownTriangle]", 13}
  },
  PlotStyle -> {
    Directive[okBlue, AbsoluteThickness[2]],
    Directive[okVerm, AbsoluteThickness[2]],
    Directive[okTeal, AbsoluteThickness[2]],
    Directive[okPurp, AbsoluteThickness[2], Dashed],
    Directive[okBlack, AbsoluteThickness[2], Dashed]
  },
  PlotLegends -> Placed[
    LineLegend[Automatic, legend, LegendMarkerSize -> 20, LabelStyle -> fsTick],
    {0.27, 0.78}
  ],
  Frame -> True,
  FrameLabel -> {Style["steering strength s", fsAxis],
    Style["best ratio over baseline", fsAxis]},
  FrameTicksStyle -> fsTick,
  PlotLabel -> Style["Strength response, all five grid cells", fsTitle],
  GridLines -> {None, {{1, Directive[Dashed, GrayLevel[0.45]]}}},
  ImageSize -> 520,
  AspectRatio -> 0.7,
  ImagePadding -> {{70, 10}, {45, 30}},
  PlotRangePadding -> Scaled[0.05]
];

fig4 = GraphicsGrid[{
    {randomPanel["random_inject_gemma_426k.json",
      "Gemma 2 2B \[Times] mntss 426K  (target \[OpenCurlyDoubleQuote]around\[CloseCurlyDoubleQuote], s = 25)"],
     randomPanel["random_inject_llama_524k.json",
      "Llama 3.2 1B \[Times] mntss 524K  (target \[OpenCurlyDoubleQuote]that\[CloseCurlyDoubleQuote], s = 25)"]},
    {randomPanel["random_inject_qwen3_0.6b_16k.json",
      "Qwen3-0.6B \[Times] BlueLightAI 16K  (target \[OpenCurlyDoubleQuote]myself\[CloseCurlyDoubleQuote], s = 25)"],
     strengthPanel}
  },
  ImageSize -> 1060, Spacings -> {10, 10}
];

Export[FileNameJoin[{figDir, "fig_random_controls.pdf"}], fig4];
Print["Exported fig_random_controls.pdf"];
