# F05 構造的損切り：failed reclaim event-sequence 分析 v1

## 1. 対象

固定pips SLは対象外とした。

起点イベントは次のとおり。

1. F05 Entry後、最初のcompleted M5まで実行可能利益へ一度も到達しない
2. 最初のcompleted M5がbreakout levelの2pips以上内側でcloseする

従来の即時退出は、この時点で次のM1 openへ退出するものだった。しかしLongでは回復可能なretestを多く切るため、今回はその後のevent sequenceを分析した。

## 2. 新しい中心所見：failed reclaim

有力だった順序は次のとおり。

1. 最初のM5でbreakout range内へ再侵入
2. その後、一度はM1 closeでbreakout level外側を回復
3. ただし実行可能利益へ到達しない
4. そのreclaim後の次のcompleted M5で再びrange内へclose
5. 次のM1 openで退出

これは単純な「初回再侵入」ではなく、**一度試みたreclaimが成立しなかったこと**を無効化条件にする。

## 3. Basic failed reclaim

追加制約なしのbasic ruleでは次の結果となった。

- stopped trades: 14
- Losers: 10
- Winners: 4
- total delta: +202.1 pips
- Long delta: +65.2 pips
- Short delta: +136.9 pips
- Winner damage: -84.9 pips
- Loser benefit: +287.0 pips
- 4fold total delta: すべて正

Fold別：

| Fold | Total | Long | Short | Stopped | Winner stopped |
|---|---:|---:|---:|---:|---:|
| 2023H1 | +70.8 | +4.6 | +66.2 | 4 | 1 |
| 2023H2 | +14.1 | -4.2 | +18.3 | 4 | 2 |
| 2024H1 | +110.7 | +58.3 | +52.4 | 5 | 1 |
| 2024H2 | +6.5 | +6.5 | 0.0 | 1 | 0 |

単純な初回再侵入ではLong合計が-206.7pipsだったが、failed reclaimではLong合計が+65.2pipsへ改善した。

ただし2023H2 Longは-4.2pipsであり、fold×directionの完全な非負条件はまだ満たさない。

## 4. Weak-and-quick failed reclaim

探索上、次の追加条件を持つ近傍仕様がより良好だった。

- reclaim外側closeの連続が2本以下
- 最初のreclaimがEntry後60分以内
- 次のcompleted M5がrange内へ戻る
- reclaimから失敗M5まで実行可能利益へ到達しない

結果：

- stopped trades: 11
- Losers: 9
- Winners: 2
- total delta: +248.3 pips
- minimum fold delta: +6.5 pips
- Long delta: +74.8 pips
- Short delta: +173.5 pips
- Winner damage: -36.6 pips
- Loser benefit: +284.9 pips

Fold別：

| Fold | Total | Long | Short | Stopped | Winner stopped |
|---|---:|---:|---:|---:|---:|
| 2023H1 | +68.7 | +2.5 | +66.2 | 3 | 1 |
| 2023H2 | +50.7 | -4.2 | +54.9 | 3 | 1 |
| 2024H1 | +122.4 | +70.0 | +52.4 | 4 | 0 |
| 2024H2 | +6.5 | +6.5 | 0.0 | 1 | 0 |

この追加条件は結果後の探索から得たため、現段階ではconfirmatory candidateではない。mechanism近傍の探索所見として扱う。

## 5. Leave-one-fold-out探索

自然な小規模familyについて、3foldで候補を選び残り1foldへ適用した。

Holdout total delta：

- 2023H1: +68.7 pips
- 2023H2: +14.1 pips
- 2024H1: +46.5 pips
- 2024H2: +6.5 pips

全holdoutでtotalは正だった。

ただし2023H2 Longは-4.2pipsであり、方向別portable gateは未通過。

## 6. 効果の性質

failed reclaim eventは最終Lossを高精度に分類するイベントではない。

Initial-trigger 58件のうち：

- Basic failed reclaim: 14件、Loser 10、Winner 4
- Refined failed reclaim: 11件、Loser 9、Winner 2

統計的なWinner/Loss分類より、**切られるLoserの後続損失が大きく、切られるWinnerの利益が比較的小さいという損益非対称**によって効果が生じている。

Refined event対象の中央値：

- 全体 baseline: -24.4 pips
- Loser baseline: -36.7 pips
- Winner baseline: +14.55 pips
- 1件あたり平均delta: +22.57 pips

## 7. 日付・月への集中

Refined ruleのfold別効果：

- 2023H1: best date除外後 +2.5pips
- 2023H2: best date除外後 +7.6pips
- 2024H1: best date除外後 +70.0pips
- 2024H2: 1件のみで +6.5pips

best two dates除外後は2023H1と2023H2が負になる。

したがって、4fold totalは正でもbreadthはまだ弱い。特に2024H2は1件のみで、独立した再現証拠として弱い。

## 8. 2024 Tick感度

2024の初回M5 triggerはM1基準で27件。

Tick exact MFEを確認すると、そのうち4件は最初の5分内に一時的な正の実行可能P/Lを記録していた。M1 high/lowだけではイベント順序を完全には表現できない。

一方、Refined failed reclaimで実際に停止した2024の5件は、全件で最初の5分のTick exact MFEが非正だった。

したがって、現在の有力eventに関しては2024の初回arming条件はTickでも維持された。

次のconfirmatory protocolでは、2024はTick exact ordering、2023はM1 common contractとして別々に監査する必要がある。

## 9. 現時点の解釈

F05の損切りに必要なのは、

- 最初のbreakout失敗だけではない
- 単なる時間経過でもない
- 固定逆行幅でもない

**re-entry → reclaim attempt → reclaim failure**

という状態遷移である可能性が高い。

Longで回復するtradeは、初回再侵入後にreclaimを利益状態へつなげる。一方、失敗tradeはbreakout外側へ一時的に戻っても、その状態を次のM5まで保持できない。

## 10. 現在の判定

- 単純な初回M5再侵入即時退出：方向非対称により候補化不可
- Basic failed reclaim：有力な探索所見
- Weak-and-quick failed reclaim：さらに有力だが結果後探索
- Confirmatory candidate：未凍結
- Portfolio replay：未実施
- MT4/TDS：未実施
- 2025：未アクセス

## 11. 次の研究

1. 2024 Tickでreclaim発生・利益化・再失速の厳密な順序を再構築
2. 2023 M1 common contractとのsemantic parityを定義
3. thresholdを増やさず、Basic failed reclaimと1つの近傍仕様にfamilyを限定
4. outcome-free preregistration
5. GitHub Actionsで4fold Research portfolio replay
6. 通過時のみMT4/TDS parityへ進む

この分析だけでは実装を認可しない。
