## ハフモデル分析ツール for ArcGIS Pro

ハフモデル分析ツールは、商圏分析によく使われるハフモデルについて、ArcGIS Pro上で一括して処理できるようにしたツールです。下記からダウンロード（右クリックして保存）できます。詳細については下記のとおりですが、授業用に作成したものであるため、予期せぬ動作をしてしまったり、別のデータでは不具合が生じてしまったり、ということがあるかもしれません。不具合についてはご一報いただければ対応することも考えますが、基本的には自己責任でご利用ください。本ツールの著作権は桐村が有します。ハフモデルの解説については[こちら](https://business-map.esrij.com/glossary/2021/)などをご覧ください。

### ArcGIS Proで使用する手順

1. ダウンロードしたファイルを、任意の場所に配置します。ArcGIS Proのプロジェクトファイルがあるフォルダーに置くとアクセスがしやすいでしょう。
2. ArcGIS Proを起動し、カタログから先ほど配置したフォルダーを開きます。
3. huffmodel.pytを探し、ダブルクリックすると、「ハフモデル分析」が表示されますので、それをダブルクリックして起動します。

### パラメーターの解説

1. **店舗レイヤー（ポイント）**
  店舗を示すポイントデータを選んでください。
1. **魅力度フィールド**
  店舗レイヤーに含まれる魅力度を示すフィールドを選んでください。
1. **需要レイヤー（ポイント）**
  人口などの需要を表すポイントデータを選んでください。ポイントデータがない場合は、フィーチャ→ポイント（Feature To Point）などで変換しておきましょう。
1. **集計フィールド**
  需要レイヤーにある、需要として集計する、人口などのフィールドを選んでください。
1. **距離抵抗**
  1.0～2.0の任意の値を入れてください。距離抵抗とは、距離の何乗なのかを示す数値です。特に決めていなければデフォルトのままにしましょう。
1. **検索半径**
  メートル単位の検索半径を設定します。ここで指定した範囲まで解析されますので、もし距離について特に問わない（制限しない）のであれば、分析に用いるデータがすべて入ってしまうような半径を指定してください。
1. **出力テーブル**
  結果はテーブルとして出力されますので出力先を指定してください。

### ダウンロードはこちらから
[ハフモデル分析ツール](./huffmodel.pyt) 拡張子がpytのPythonツールボックス形式です。右クリックして保存してください。

2021.03.29公開
