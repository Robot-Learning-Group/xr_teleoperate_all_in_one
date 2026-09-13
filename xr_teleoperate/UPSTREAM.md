# 取り込み元

このディレクトリは `xr_teleoperate_all_in_one` が直接管理する通常のファイルです。
独立した Git リポジトリや Git submodule ではありません。変更のコミット・push は親リポジトリだけで行います。

- 公式: https://github.com/unitreerobotics/xr_teleoperate
- 元コミット: `817fb00c63cde15e5f24a0f8fa08e1e33ed89d3b`
- 取り込み日: 2026-09-13
- 配布アーカイブ: https://api.github.com/repos/unitreerobotics/xr_teleoperate/tarball/817fb00c63cde15e5f24a0f8fa08e1e33ed89d3b
- 使用したアーカイブの SHA-256: `21c252184476cff222e3f150cb4f8268930e67f0c1c369821d9d086a41054069`

取り込み時に、全406ファイルの内容を公式 Git tree の blob ハッシュと照合しました。
Git 履歴は取り込まず、公式の `LICENSE` と各ファイルの著作権表示を保持しています。

取り込みに伴う差分:

- `.gitmodules` を除外。そこで指定されていた3依存の URL とコミットを、親の `docker/repos.lock` に記録。
- `.gitignore` に、初回の追加時も公式アセットを含める設定と、実行時の記録データを除外する設定を追加。
- この `UPSTREAM.md` を追加。
- Python コード・ロボットモデル・その他の公式ファイルは取り込み時点では変更なし。

`televuer`・`teleimager`・`dex-retargeting` は、他の依存とまとめて Docker ビルド時に `/opt/src/` へ取得してインストールします。編集用の `/opt/src/xr_teleoperate/` の外に配置されます。
公式 README にある `git submodule update` や旧配置パスの手順は、この同梱版には適用しません。
ビルド・起動・編集方法は親の [README](../README.md) を参照してください。

公式への追従時は、上記コミットを比較の基準にしてください。必要な変更を取り込み、依存コミットとこの記録も更新します。
