(* ::Package:: *)

(* ================================================================== *)
(* BlackboxNLP 2026 Reproducibility Challenge paper figures            *)
(* Data: committed candle-mi grid JSONs, copied into ../data           *)
(* Run:  wolframscript -file scripts/make_figures.wl                   *)
(* Output: ../figures/fig_position_sweep.pdf, fig_strength.pdf,        *)
(*         fig_newline_horizon.pdf                                     *)
(* Note (2026-07-15): original compact font sizes retained by choice;  *)
(* readers zoom the vector PDF. Newline token labels are orange to     *)
(* match their bars.                                                   *)
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
okBlack = GrayLevel[0.1];

loadCell[file_] := Import[FileNameJoin[{dataDir, file}], "RawJSON"];
rowAt[d_, s_] := SelectFirst[d["sweep_grid"], #["strength"] == s &]["sweep"];
cleanToken[t_] := StringReplace[t, {"<|begin_of_text|>" -> "<bos>",
  "\n" -> "\\n", " " -> "\[ThinSpace]"}];

(* Token labels: Consolas; newline tokens in the same orange as their bars. *)
styledTokenLabels[tokens_] := MapIndexed[
  Style[cleanToken[#1], 7, FontFamily -> "Consolas",
    If[StringContainsQ[#1, "\n"], okVerm, GrayLevel[0]]] &,
  tokens
];

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
    PlotLabel -> Style[title, 11],
    FrameLabel -> {None, Style["P(\"" <> d["inject_word"] <> "\")", 10]},
    Frame -> True,
    FrameTicksStyle -> 8,
    BarSpacing -> 0.15,
    ImageSize -> 460,
    AspectRatio -> 0.62,
    ImagePadding -> {{52, 8}, {58, 24}},
    PlotRangePadding -> {{Scaled[0.01], Scaled[0.01]}, {0, Scaled[0.08]}},
    GridLines -> {None, {{d["baseline_prob"],
        Directive[Dashed, GrayLevel[0.45]]}}},
    Epilog -> {
      Text[Style["baseline", 7, GrayLevel[0.35]],
        Scaled[{0.08, 0.10}]],
      Text[Style[
        Row[{"P = ",
          If[probs[[imax]] < 0.01,
            ScientificForm[probs[[imax]], 3],
            NumberForm[probs[[imax]], {4, 3}]]}], 8, okBlue],
        Scaled[{0.78, 0.94}]]
    }
  ]
];

gemma  = loadCell["figure13-gemma-426k/figure13_out_grid.json"];
llama  = loadCell["figure13-llama-524k/figure13_ee_grid.json"];
q06t   = loadCell["figure13-qwen3-0.6b-20k/figure13_teen_grid.json"];
q17t   = loadCell["figure13-qwen3-1.7b-20k/figure13_teen_grid.json"];
q06a16 = loadCell["figure13-qwen3-0.6b-16k/figure13_ation_grid_v2.json"];

fig1 = GraphicsRow[{
    sweepPanel[gemma, 25.,
      "Gemma 2 2B \[Times] mntss 426K   (\[Minus]out \[RightArrow] \[OpenCurlyDoubleQuote]around\[CloseCurlyDoubleQuote], s=25)"],
    sweepPanel[llama, 25.,
      "Llama 3.2 1B \[Times] mntss 524K   (\[Minus]ee \[RightArrow] \[OpenCurlyDoubleQuote]that\[CloseCurlyDoubleQuote], s=25)"],
    sweepPanel[q06t, 1.,
      "Qwen3-0.6B \[Times] BlueLightAI 20K   (\[Minus]teen \[RightArrow] \[OpenCurlyDoubleQuote]duration\[CloseCurlyDoubleQuote], s=1)"]
  },
  ImageSize -> 1420, Spacings -> 0
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
    {"\[FilledCircle]", 9}, {"\[FilledSquare]", 9},
    {"\[FilledUpTriangle]", 10}, {"\[FilledDiamond]", 10},
    {"\[FilledDownTriangle]", 10}
  },
  PlotStyle -> {
    Directive[okBlue, AbsoluteThickness[1.6]],
    Directive[okVerm, AbsoluteThickness[1.6]],
    Directive[okTeal, AbsoluteThickness[1.6]],
    Directive[okPurp, AbsoluteThickness[1.6], Dashed],
    Directive[okBlack, AbsoluteThickness[1.6], Dashed]
  },
  PlotLegends -> Placed[
    LineLegend[Automatic, legend, LegendMarkerSize -> 16,
      LabelStyle -> 9],
    {0.17, 0.74}
  ],
  Frame -> True,
  FrameLabel -> {
    Style["steering strength s", 11],
    Style["best ratio over baseline", 11]
  },
  FrameTicksStyle -> 9,
  GridLines -> {None, {{1, Directive[Dashed, GrayLevel[0.45]]}}},
  ImageSize -> 480,
  AspectRatio -> 0.75,
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
    PlotLabel -> Style[title, 11],
    FrameLabel -> {None,
      Style["P(\"" <> d["inject_word"] <> "\") at final-word slot", 9]},
    Frame -> True,
    FrameTicksStyle -> 8,
    BarSpacing -> 0.15,
    ImageSize -> 460,
    AspectRatio -> 0.62,
    ImagePadding -> {{52, 8}, {58, 24}},
    PlotRangePadding -> {{Scaled[0.01], Scaled[0.01]}, {0, Scaled[0.08]}},
    Epilog -> {
      Text[Style["newline", 20, okVerm],
        Scaled[{(nlIdx + 0.5)/Length[m4], 0.76}]],
      {okVerm, Arrowheads[0.02],
        Arrow[{Scaled[{(nlIdx + 0.5)/Length[m4], 0.69}],
               Scaled[{(nlIdx + 0.5)/Length[m4], 0.18}]}]},
      Text[Style[
        Row[{"P = ",
          If[probs[[imax]] < 0.01,
            ScientificForm[probs[[imax]], 3],
            NumberForm[probs[[imax]], {4, 3}]]}], 20, okBlue],
        Scaled[{0.72, 0.93}]]
    }
  ]
];

fig3 = GraphicsRow[{
    horizonPanel["figure13-newline/fullline_gemma2-2b-426k.json",
      "Gemma 2 2B \[Times] mntss 426K   (group-level, s=25)"],
    horizonPanel["figure13-newline/fullline_gemma2-2b-2.5m.json",
      "Gemma 2 2B \[Times] mntss 2.5M   (word-level, s=10)"],
    horizonPanel["figure13-newline/fullline_llama3.2-1b-524k.json",
      "Llama 3.2 1B \[Times] mntss 524K   (group-level, s=25)"]
  },
  ImageSize -> 1420, Spacings -> 0
];

Export[FileNameJoin[{figDir, "fig_newline_horizon.pdf"}], fig3];
Print["Exported fig_newline_horizon.pdf"];
