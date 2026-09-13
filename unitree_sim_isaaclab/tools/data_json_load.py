import json
import numpy as np
import torch
import re
from pathlib import Path
def convert_nested_lists_to_tensor(obj):
    """
    递归遍历 obj，把所有形如 list[list[float]] 的结构转为 torch.tensor。
    """
    if isinstance(obj, dict):
        return {k: convert_nested_lists_to_tensor(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # 判断是否是 list[list[number]]
        if all(isinstance(item, list) and all(isinstance(x, (int, float)) for x in item) for item in obj):
            return torch.tensor(obj, dtype=torch.float32)
        else:
            return [convert_nested_lists_to_tensor(item) for item in obj]
    else:
        return obj
def load_robot_data(json_path):
    """
    读取并解析 robot data.json 文件，并将 sim_state 中所有 list[list[float]] 转为 tensor。

    参数:
        json_path (str): JSON 文件路径

    返回:
        tuple: (robot_action: List[np.ndarray], hand_action: List[np.ndarray], sim_state: dict with torch.tensor)
    """
    with open(json_path, 'r') as f:
        content = json.load(f)

    info = content.get("info", {})
    text = content.get("text", {})
    data = content.get("data", [])


    if not data:
        raise ValueError("data is None")

    robot_action = []
    hand_action = []
    sim_state_json_list=[]
    sim_state_list=[]
    sim_task_name_list=[]
    for item in data:
        action = item.get("actions", {})
        if not action:
            raise ValueError("data not have action")

        left_arm = action.get("left_arm", {})
        right_arm = action.get("right_arm", {})
        left_arm_action = np.array(left_arm.get("qpos", []))
        right_arm_action = np.array(right_arm.get("qpos", []))
        left_right_arm = np.concatenate([left_arm_action, right_arm_action])

        left_hand = action.get("left_ee", {})
        right_hand = action.get("right_ee", {})
        left_hand_action = np.array(left_hand.get("qpos", []))
        right_hand_action = np.array(right_hand.get("qpos", []))
        left_right_hand = np.concatenate([right_hand_action, left_hand_action])

        robot_action.append(left_right_arm)
        hand_action.append(left_right_hand)
        sim_state_json = item.get("sim_state", "{}")
        if not sim_state_json:
            raise ValueError("sim_state is None")
        sim_state_json_list.append(sim_state_json)
        # sim_state = parse_nested_sim_state(sim_state_json)
        sim_state_raw = sim_state_json.get("init_state","{}")
        task_name = sim_state_json.get("task_name","")
        if task_name=="":
            raise ValueError("task_name is None")
        # 如果 sim_state 是 JSON 字符串则解析
        if not sim_state_raw:
            raise ValueError("sim_state_raw is None")
        if isinstance(sim_state_raw, str):
            sim_state_dict = json.loads(sim_state_raw)
        else:
            sim_state_dict = sim_state_raw
        sim_state = convert_nested_lists_to_tensor(sim_state_dict)
        sim_state_list.append(sim_state)
        sim_task_name_list.append(task_name)
    return robot_action, hand_action, sim_state_list,sim_task_name_list,sim_state_json_list



def load_robot_data2(json_path):
    """
    读取并解析 robot data.json 文件，并将 sim_state 中所有 list[list[float]] 转为 tensor。

    参数:
        json_path (str): JSON 文件路径

    返回:
        tuple: (robot_action: List[np.ndarray], hand_action: List[np.ndarray], sim_state: dict with torch.tensor)
    """
    with open(json_path, 'r') as f:
        content = json.load(f)

    info = content.get("info", {})
    text = content.get("text", {})
    data = content.get("data", [])
    sim_state = info.get("sim_state", "{}")
    if not sim_state:
        raise ValueError("sim_state is None")
    sim_state = parse_nested_sim_state(sim_state)
    sim_state_raw = sim_state.get("init_state","{}")
    task_name = sim_state.get("task_name","")

    if task_name=="":
        raise ValueError("task_name is None")
    # 如果 sim_state 是 JSON 字符串则解析
    if not sim_state_raw:
        raise ValueError("sim_state_raw is None")
    if isinstance(sim_state_raw, str):
        sim_state_dict = json.loads(sim_state_raw)
    else:
        sim_state_dict = sim_state_raw

    # 转换 sim_state 所有符合条件的嵌套 list -> tensor
    sim_state = convert_nested_lists_to_tensor(sim_state_dict)

    if not data:
        raise ValueError("data is None")

    robot_action = []
    hand_action = []

    for item in data:
        action = item.get("actions", {})
        if not action:
            raise ValueError("data not have action")

        left_arm = action.get("left_arm", {})
        right_arm = action.get("right_arm", {})
        left_arm_action = np.array(left_arm.get("qpos", []))
        right_arm_action = np.array(right_arm.get("qpos", []))
        left_right_arm = np.concatenate([left_arm_action, right_arm_action])

        left_hand = action.get("left_ee", {})
        right_hand = action.get("right_ee", {})
        left_hand_action = np.array(left_hand.get("qpos", []))
        right_hand_action = np.array(right_hand.get("qpos", []))
        left_right_hand = np.concatenate([right_hand_action, left_hand_action])

        robot_action.append(left_right_arm)
        hand_action.append(left_right_hand)

    return robot_action, hand_action, sim_state,task_name


def parse_nested_sim_state(json_str: str):
    # 第一步：解析外层 JSON
    outer = json.loads(json_str)

    # 第二步：解析内层 JSON（init_state 是字符串）
    if "init_state" in outer and isinstance(outer["init_state"], str):
        outer["init_state"] = json.loads(outer["init_state"])

    return outer

def get_file_path(dir):
    root_dir = Path(dir)
    json_paths = list(root_dir.glob("**/data.json"))
    pathlist = [str(p) for p in json_paths]
    return pathlist

def get_data_json_list(file_path):
    print(f"args_cli.file_path:{file_path}")
    file_path = Path(file_path)
    data_json_list=[]
    if file_path.is_file():
        if file_path.suffix == ".json":
            data_json_list.append(file_path)
        else:
            raise ValueError("file is error")
    elif file_path.is_dir():
        data_json_list = get_file_path(file_path)

    # 按照episode_后面的数字排序
    def extract_episode_number(path):
        match = re.search(r'episode_(\d+)', str(path))
        return int(match.group(1)) if match else float('inf')
    
    data_json_list.sort(key=extract_episode_number)
    
    print(f"data_json_list: {data_json_list}")
    return data_json_list

def tensors_to_list(obj):
    if isinstance(obj, torch.Tensor):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: tensors_to_list(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [tensors_to_list(i) for i in obj]
    return obj

def sim_state_to_json(data):
    data_serializable = tensors_to_list(data)
    json_str = json.dumps(data_serializable)
    return json_str