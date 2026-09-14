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

初回は `docker/.env.example` を `docker/.env` にコピーし、`IMG_SERVER_IP` をQuestから接続できる画像サーバーPCのLAN IPに設定します。

```bash
# docker/ 内：シミュレーション（G1＋Dex3、円柱）
docker compose run --rm sim sim
```

```bash
# 別のデスクトップ端末・リポジトリルート：XR
./docker/teleop.sh
```

Questで `https://<XRを動かすPCのIP>:8012/` を開き、証明書の警告が出た場合は承認してください。

`r`：追従開始、`s`：記録開始／保存、`q`：終了。

## 実機での起動

`docker/.env` の `IMG_SERVER_IP` を画像サーバーPCのIP、`NETWORK_INTERFACE` を実機に接続したNIC名に設定します。

画像サーバーが未起動の場合、カメラPCの `docker/cam_config_server.yaml` を編集して起動します（デバイスは使用するカメラに合わせます）。

```bash
# カメラPCの docker/ 内
docker compose run --rm \
  -v /dev/video0:/dev/video0 -v /dev/bus/usb:/dev/bus/usb image-server
```

```bash
# リポジトリルート：腕のみ、記録有効
./docker/teleop-real.sh
```

## ハンドの変更

| ハンド | Sim起動（`docker/` 内） | XR起動（ルート） |
| --- | --- | --- |
| Dex3（3指） | `docker compose run --rm sim sim` | `./docker/teleop.sh --ee dex3` |
| Revo2（5指） | `docker compose run --rm sim sim-brainco` | `./docker/teleop.sh --ee brainco` |

実機も `./docker/teleop-real.sh --ee brainco` のように指定します。実機側では対応するハンド通信サービスの起動が必要です。

素手のトラッキングはXR起動コマンドに `--input-mode hand` を追加します。既定はコントローラーです。

## タスクの変更

Sim起動時に `--task` を追加します。

```bash
# 赤いブロック（Dex3）
docker compose run --rm sim sim --task Isaac-PickPlace-RedBlock-G129-Dex3-Joint

# 赤いブロックを引き出しに入れる（Dex3）
docker compose run --rm sim sim --task Isaac-Pick-Redblock-Into-Drawer-G129-Dex3-Joint
```

XR側の起動コマンドは同じです。Revo2は現在、円柱タスクのみ対応しています。

## データセット名の変更

XR起動時に `--task-name` を指定します。

```bash
./docker/teleop.sh --task-name red_block_01
./docker/teleop-real.sh --task-name real_pick_01
```

ホストの `data/<指定した名前>/episode_XXXX/` に保存します。同じ名前で再起動するとエピソードを追加します。
