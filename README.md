# XR Teleoperate

`docker compose` は `docker/` 内、`./docker/…` はリポジトリルートで実行します。

## ビルド

```bash
cd docker
docker compose build      # 両方
# 必要な方だけ
docker compose build xr   # テレオペ
docker compose build sim  # シミュレーション
```

## シミュレーションとXRの起動

1. `docker/.env` のIMG_SERVER_IP` をQuestから接続できる画像サーバーPCのLAN IPに設定します。
2. シミュレーションの起動
```bash
./docker/sim.sh
```
3. テレオペの起動
```bash
./docker/teleop-sim.sh
```

Questで `https://<XRを動かすPCのIP>:8012/` を開き、証明書の警告が出た場合は承認してください。

`r`：追従開始、`s`：記録開始／保存、`q`：終了。

## 実機での起動

1. `docker/.env` の `IMG_SERVER_IP` を画像サーバーPCのIP、`NETWORK_INTERFACE` を実機に接続したNIC名に設定します。
2. コントローラのL2＋R2を長押しして、G1をDeveloperモードにする
3. テレオペ起動

```bash
./docker/teleop-real.sh
```

## 3指、5指の切り替え
コマンドの末尾に以下を付ける。
```bash
# 3指ハンド
./docker/teleop-real.sh　--ee dex3
# 5指ハンド
./docker/teleop-real.sh　--ee brainco
```
何も指定しなかったら3指ハンドになる。
## コントローラ、ハンドトラッキングの切り替え
コマンドの末尾に以下を付ける

```bash
# ハンドトラッキング
./docker/teleop-real.sh　--input-mode hand
# コントローラ
./docker/teleop-real.sh　--input-mode controller
```
何も指定しなかったらコントローラになる。
## タスクの変更

Sim起動時に `--task` を追加します。

```bash
# 赤いブロック（Dex3）
./docker/sim.sh --task Isaac-PickPlace-RedBlock-G129-Dex3-Joint

# 赤いブロックを引き出しに入れる（Dex3）
./docker/sim.sh --task Isaac-Pick-Redblock-Into-Drawer-G129-Dex3-Joint
```

XR側の起動コマンドは同じです。Revo2は現在、円柱タスクのみ対応しています。

## データセット名、言語指示の変更

データセット名は`--task-name` を、言語指示は'--task-goal'を指定します。

```bash
./docker/teleop-sim.sh --task-name red_block_01　--task-goal "pick up the red block"
```

ホストの `data/<指定した名前>/episode_XXXX/` に保存します。同じ名前で再起動するとエピソードを追加します。
