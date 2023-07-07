"""This file run test api get and post."""
"""
File: run.py 
Version: 0.1
Updated: 2023-07
Author: Tang
"""

from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Union, Optional, List, Dict
import json
from pydantic import BaseModel
import os
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, status, Request, Response, HTTPException, Header,Body


app_decription = """
# 机器人后端API说明

目前支持HTTP协议，WS 接口未开发。

## 更新说明
1.更新了验证模型数据输入验证
2.增加了新的请求方法
 
"""

app = FastAPI(title='机器人后端API说明', description=app_decription)
app.version = "0.2"

"""# 通用响应模型返回的数据格式
"""


class LastErrorBase(BaseModel):
    """### 返回最后操作的错误码和错误信息
    - 参数
        - **ERROR_TYPE**: str,错误类型
        - **code**: int,错误值
        - **message**: str,错误信息
    """
    ERROR_TYPE: str = ""
    code: int = 0
    message: str = "没有错误"


LastError = LastErrorBase()


class ResponseReturn(BaseModel):
    """# 通用响应模型返回的数据格式
    - **status**: bool,请求状态 True 成功  False 失败
    - **code**: int,状态码 0 成功  -1 失败
    - **message**: str,消息
    - **data**: dict,数据
    """
    status: bool = False
    code: int = -1
    message: str = ""
    data: Union[dict, LastErrorBase] = LastErrorBase()


# ResponseReturn = ResponseReturn()
"""END
# 通用响应模型返回的数据格式
"""

"""# UserManage 用户管理模块
"""
# 用户数据库
UsersDB = {
    "test": {
        "username": "test",
        "hashed_password": "$2b$12$O5g5t0DKQkAZy6vt7JB6deH6NMS9cUNyFtZeeNsPtk83KPVjs5e92",
        "disabled": False,
        "permissions": ["guest", "post:read"]
    },
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$cJn24OGIxnq1bbzwg1fc1OhlXpjYrvCnzQcU0ipCqTlDFdPET9xfa",
        "disabled": False,
        "permissions": ["administator", "post:wirtes"]
    }
}

"""# 用户管理模块，用户认证吗，权限管理
"""
class UserInput(BaseModel):
    """## 用户输入模型
        - **username**: str,用户名
        - **password**: str,密码
    """
    username: str = "admin"  # 用户名
    password: str = "abcd1234"  # 密码

# to get a string like this run in git bash:
# openssl rand -hex 32
# e5d05487248b25c0c95b1d36598a202b3b4bda99d555d31aefc3dddcfb1ad7e6
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30
ACCESS_TOKEN_EXPIRE_HOURS = 24
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UserManage:
    """#  用户管理模块，用户认证吗，权限管理
    """
    # 密码加密
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # pwd_context.hash("dc123456")
    # pwd_context.verify(password, hashed_password)):
    user_current_id = ""  # 当前用户ID
    user_token = ""  # 当前用户token
    users_db = UsersDB  # 用户数据库

    def username_verify(self, username: str) -> bool:
        """# 用户名验证
        - **username**: str,用户名
        # 返回值:用户名存在返回True,否则返回False
        """
        if username in self.users_db:
            self.user_current_id = username
            return True
        return False

    def password_verify(self, password: str) -> bool:
        """# 用户密码验证
        - **password**: str,密码
        # 返回值:密码正确返回True,否则返回False
        """
        if self.password_hash_check(password, self.users_db[self.user_current_id].get("hashed_password")):
            return True
        return False

    def check_permissions(self, permissions: str, token: str = Header("token")):
        """# 用户权限验证
        - **permissions**: str,权限
        # 返回值:权限正确返回True,否则返回False
        """
        def check_authorization(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
                if permissions in self.users_db[self.user_current_id].get("permissions"):
                    return func(*args, **kwargs)
                return False
            return wrapper
        return check_authorization

    def password_hash(self, password: str) -> str:
        # 用户密码哈希值加密
        return self.pwd_context.hash(password)

    def password_hash_check(self, password: str, hashed_password: str) -> bool:
        # 用户密码哈希值验证
        if self.pwd_context.verify(password, hashed_password):
            return True
        else:
            return False

    def token_get(self, user_id: str) -> str:
        # 生成token
        to_encode = {"sub": self.user_current_id}
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        to_encode.update({"exp": expire})
        user_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return user_token

    def get_current_username(self, token: str) -> Union[str, None]:
        # 验证token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                LastError.ERROR_TYPE = "TOKEN_ERROR"
                LastError.code = 2
                LastError.message = "Token 验证用户不存在:username is None"
                return None
            return username
        except JWTError:
            LastError.ERROR_TYPE = "TOKEN_ERROR"
            LastError.code = 2
            LastError.message = "Token 验证错误：JWTError"
            return None


GUserManage = UserManage()

"""END
用户管理模块UserManage
"""


"""
用户管理模块 请求路径与方法
"""


@app.post("/login", summary="用户登录，返回token值", tags=["用户管理"])
async def user_login(user: UserInput) -> ResponseReturn:
    """# 用户登录，返回token值
    - Parameters:
        - **username**: string, 用户名
        - **password**: string, 密码
    - example:
        - {"user":{"username": "admin", "password": "abcd1234"}}
    # 返回值:
    - response:
        - {"token":string(token值)}
    """
    LastError = LastErrorBase()
    if not GUserManage.username_verify(user.username):
        LastError.ERROR_TYPE = "USER_LOGIN_ERROR"
        LastError.code = 1
        LastError.message = "用户名不存在"
        return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)
    if not GUserManage.password_verify(user.password):
        LastError.ERROR_TYPE = "USER_LOGIN_ERROR"
        LastError.code = 1
        LastError.message = "用户密码错误"
        return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)
    return ResponseReturn(status=True, code=0, message="用户登录:"+user.username, data={"token": GUserManage.token_get(user.username)})


@app.get("/login/me", summary="获取当前登录用户的信息", tags=["用户管理"])
async def user_read_me(request: Request) -> ResponseReturn:
    """# 返回当前登录用户的信息
    - Parameters:
    - response:
        - {"username":username}
    """
    global LastError
    LastError = LastErrorBase()
    username = GUserManage.get_current_username(request.headers.get('token'))
    if username is None:
        return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)
    return ResponseReturn(status=True, code=0, message="获取当前登录用户的信息", data={"username": username})


@app.post("/user/login", summary="用户登录，返回token值", tags=["用户管理"],response_model_exclude={BaseModel})
async def user_login_2(user: UserInput) -> ResponseReturn:
    """# 用户登录，返回token值
    - Parameters:
        - **username**: string, 用户名
        - **password**: string, 密码
    - example:
        - {"user":{"username": "admin", "password": "abcd1234"}}
    # 返回值:
    - response:
        - {"token":string(token值)}
    """
    LastError = LastErrorBase()
    if not GUserManage.username_verify(user.username):
        LastError.ERROR_TYPE = "USER_LOGIN_ERROR"
        LastError.code = 1
        LastError.message = "用户名不存在"
        return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)
    if not GUserManage.password_verify(user.password):
        LastError.ERROR_TYPE = "USER_LOGIN_ERROR"
        LastError.code = 1
        LastError.message = "用户密码错误"
        return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)
    return ResponseReturn(status=True, code=0, message="用户登录:"+user.username, data={"token": GUserManage.token_get(user.username)})

"""END
用户管理模块 请求路径与方法
"""

"""# 视觉管理模块
"""
class VisionBase(BaseModel):
    """# VisionBase模型表示视觉参数
    - ip: string, IP地址
    - port: int, 端口号
    - username: string, 用户名
    - password: string, 密码
    """
    ip: str = "192.168.1.64"
    port: int = 8000
    username: str = "admin"
    password: str = "abcd1234"

class VisionPose(BaseModel):
    """# VisionPose模型表示p、t和z参数
    - **lChannel**: int, 通道号，1-可见光，2-热成像
    - **wAction**: int, 1-定位PTZ参数，2-定位P参数，3-定位T参数，4-定位Z参数，5-定位PT参数
    - **wPanPos**: int, 云台水平方向控制，范围0-3600
    - **wTiltPos**: int, 云台垂直方向控制，范围-900-900
    - **wZoomPos**: int, 云台变倍控制，范围10-320
    """
    lChannel: int = 1  # 通道号，1-可见光，2-热成像
    wAction: int = 1  # 1-定位PTZ参数，2-定位P参数，3-定位T参数，4-定位Z参数，5-定位PT参数
    wPanPos: int = 0  # 云台水平方向控制，范围0-3600
    wTiltPos: int = 0  # 云台垂直方向控制，范围-900-900
    wZoomPos: int = 10  # 云台变倍控制，范围10-320


class VisionPreset(BaseModel):
    """# VisionPreset模型表示预置点
    - **ID**: str, 设备ID, 唯一标识，例如：'
    - **lChannel**: int, 通道号，1-可见光，2-热成像
    - **dwPTZPresetCmd**: int = 39, 命令 GOTO_PRESET = 39 
    - **dwPresetIndex**: int = 1, 预置点索引，范围1-300
    """
    ID: str = ""  # 设备ID, 唯一标识
    lChannel: int = 1  # 通道号，1-可见光，2-热成像
    dwPTZPresetCmd: int = 39  # 命令 GOTO_PRESET = 39
    dwPresetIndex: int = 1  # 预置点索引，范围1-300


class VisionEvent(BaseModel):
    # 定义事件信息返回结构
    command: int = 0  # 事件码，0-无事件
    code: int = 0  # 事件类型，0-无事件，1-人形检测，2-人形跟踪，3-人形识别，4-人形追踪识别
    message: str  # 事件信息
    other: str  # 其他信息


class VisionManage:
    """# 海康威视，微影摄像头服务模块
    """
    ip = "192.168.1.64"  # 设备ip地址
    port = 8000  # 设备端口号
    username = "admin"  # 设备用户名
    password = "dc123456"  # 设备密码

    lUserId = -1  # 登录设备返回的用户ID
    lChannel = 1  # 视频通道号，可见光1，热成像2
    LastErrorCode = -1  # 错误码
    event = VisionEvent(command=0, code=0, message="", other="")

    def __init__(self, base: VisionBase = VisionBase()):
        # 初始化设备信息
        self.ip = base.ip
        self.port = base.port
        self.username = base.username
        self.password = base.password
    def login(self,base: VisionBase = VisionBase()) -> bool:
        # 登录设备
        self.ip = base.ip
        self.port = base.port
        self.username = base.username
        self.password = base.password
        return True
    def get_pose(self,lChannel: int = 1) -> bool:
        #  获取摄像头云台位置信息
        self.pose.lChannel = lChannel
        return True

    def set_pose(self, lChannel: int = 1, wAction: int = 1, wPanPos: int = 0, wTiltPos: int = 0, wZoomPos: int = 10) -> bool:
        #  设置摄像头云台位置信息
        self.pose.lChannel = lChannel
        self.pose.wAction = wAction
        self.pose.wPanPos = wPanPos
        self.pose.wTiltPos = wTiltPos
        self.pose.wZoomPos = wZoomPos
        return True

    def preset(self, lChannel: int = 1, dwPTZPresetCmd: int = 39, dwPresetIndex: int = 1) -> bool:
        #  摄像头云台调用预置点操作
        self.lChannel = lChannel
        # self.dwPTZPresetCmd = dwPTZPresetCmd
        # self.dwPresetIndex = dwPresetIndex
        return True


GVisionManage = VisionManage()
"""END
视觉管理模块VisionManage
"""


"""
视觉管理模块 请求路径与方法
"""

@app.post("/user/vision/login", summary="登录摄像头", tags=["视觉管理"])
async def vision_login(base:VisionBase = VisionBase()) -> ResponseReturn:
    """## 登录摄像头
    - Parameters:
        - VisionBase 设备信息
            - ip: str ,  唯一标识,为ip地址
            - port: int = 8000, 设备端口号
            - username: str = "admin", 设备用户名
            - password: str = "dc123456", 设备密码
        - example:
            - {"base":{VisionBase}
    - 返回：
        - {'login':VisionBase} 登录信息
    """
    LastError = LastErrorBase()
    global GVisionManage
    GVisionManage = VisionManage(base)
    if GVisionManage.login():
        return ResponseReturn(status=True, code=0, message="Login success", data={'base': base})
    return ResponseReturn(status=False, code=LastError, message=LastError.message, data=LastError)

@app.get("/user/vision/pose", summary="获取摄像头的PTZ坐标角度信息", tags=["视觉管理"])
async def vision_get_pose(pose: VisionPose) -> ResponseReturn:
    """# 获取摄像头的PTZ坐标角度信息
    - 参数：
        - VisionPose 视觉信息
            - lChannel: int = 1, 通道号，1-可见光，2-热成像
            - 其他无效
    - 示例：
        - {'pose':VisionPose} 视觉信息
    """
    LastError = LastErrorBase()
    if GVisionManage.get_pose(pose.ID, pose.lChannel):
        return ResponseReturn(status=True, code=0, message="Get vision pose success", data={'pose': GVisionManage.pose})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/vision/pose", summary="设置摄像头的PTZ坐标角度信息", tags=["视觉管理"])
async def vision_set_pose(pose: VisionPose) -> ResponseReturn:
    """# 设置摄像头的PTZ坐标角度信息
    - 参数：
        - VisionPose 视觉信息模型
            - lChannel: int = 1, 通道号，1-可见光，2-热成像
            - wAction: int =1, 1-定位PTZ参数，2-定位P参数，3-定位T参数，4-定位Z参数，5-定位PT参数
            - wPanPos: int  =0, 云台水平方向控制，范围0-3600
            - wTiltPos: int  =0, 云台垂直方向控制，范围-900-900
            - wZoomPos: int  =10, 云台变倍控制，范围10-320
    - 示例：
        - {'pose':VisionPose} 视觉信息
    """
    LastError = LastErrorBase()
    if GVisionManage.set_pose(pose.ID, pose.lChannel, pose.wAction, pose.wPanPos, pose.wTiltPos, pose.wZoomPos):
        return ResponseReturn(status=True, code=0, message="Set vision pose success", data={'pose': GVisionManage.pose})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/vision/preset", summary="摄像头云台调用预置点操作", tags=["视觉管理"])
async def vision_preset(preset: VisionPreset) -> ResponseReturn:
    """# 摄像头云台调用预置点操作
    - 参数：
        - VisionPreset 视觉预置点模型
            - lChannel: int = 1, 通道号，1-可见光，2-热成像
            - dwPTZPresetCmd: int = 39, 预置点操作命令，39-调用预置点
            - dwPresetIndex: int = 1, 预置点索引，范围1-300,设置使用的预置点索引
    """
    LastError = LastErrorBase()
    if GVisionManage.preset(preset.lChannel, preset.dwPTZPresetCmd, preset.dwPresetIndex):
        return ResponseReturn(status=True, code=0, message="Set vision preset success")
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)
"""END
视觉管理模块 请求路径与方法
"""


"""# 机器人相关模块
"""
# 模型不支持类中定义，需要定义为全局变量

class RobotBase(BaseModel):
    """# 定义RobotBase模型参数
    - 参数：
        - ip: str = "" , 机器人ip，唯一标识，为ip地址
        - port: int = 8000, 机器人端口号
        - username: str = "admin", 机器人用户名
        - password: str = "dc123456", 机器人密码
    """
    ip: str = "1"       # 机器人ip，唯一标识，为ip地址
    port: int = 8000    # 机器人端口号
    username: str = "admin"  # 机器人用户名
    password: str = "dc123456"  # 机器人密码


class RobotPose(BaseModel):
    """# 定义RobotPose模型参数:x、y坐标和θ朝向
    - 参数：
        - x: float = 0, 任务点位置x坐标
        - y: float = 0, 任务点位置y坐标
        - theta: float = 0, 任务点朝向X角度
    """
    x: float = 0       # 任务点位置x坐标
    y: float = 0       # 任务点位置y坐标
    theta: float = 0   # 任务点朝向X角度


class RobotAction(BaseModel):
    # 定义RobotAction模型表示任务点动作参数列表
    actionContent: str = ""  # 执行动作时长，秒数
    actionType: str = ""     # 动作类型，可填值"rotation":选择 "stop":停止
    actionName: str = ""     # 动作名称
    actionOrder: int = 0    # 执行动作顺序号，0为最优先处理


class RobotPoints(BaseModel):
    # 定义RobotPoints模型表示任务点参数列表
    position: RobotPose = RobotPose()  # 任务点位置
    pointType: str = ""      # 子任务点类型 可填值 "navigation":导航点， "charge":充电点，未填写默认为导航点
    # 子任务点动作列表，目前只支持一个动作，第一个动作
    actions: List[RobotAction] = [RobotAction()]
    pointName: str = ""    # 任务点名称
    index: int = 0        # 任务点索引
    isNew: bool = False       # 是否是新建的任务点
    cpx: float = 0      # 任务点位置x坐标
    cpy: float = 0     # 任务点位置y坐标


class RobotTask(BaseModel):
    # 定义RobotTask模型表示任务点列表
    taskName: str = "task"  # 任务名称
    gridItemIdx: int = 0  # web前端显示所需要的索引
    points: List[RobotPoints] = [RobotPoints()]    # 任务点列表，详细参考下面的任务点参数表
    mode: str = ""      # 任务模式， "point":多点导航 "path":路径导航
    evadible: int = 1  # 避障模式，1避障，2停障
    mapName: str = "taskMap"   # 地图名称
    speed: int = 0.5     # 导航时的速度参数0.1-1.5M/S
    editedName: str = ""  # 任务需要重命名的名称
    remark: str = "remark"   # 备注信息
    personName: str = "tang"  # 任务创建人


class RobotRealTimePoint(BaseModel):
    # 定义RobotRealTimePoint模型表示任务点列表
    position: RobotPose = RobotPose()  # 任务点位置
    isNew: bool = False      # 注意只有"mode"="path"的路径模式下有效，决定是否是新路径点的起点
    cpx: float = 0      # 曲线点x坐标，注意只有"mode"="path"的路径模式下，曲线点有效，将线段上的某个点作为贝塞尔曲线点
    cpy: float = 0      # 曲线点y坐标，注意只有"mode"="path"的路径模式下，曲线点有效，将线段上的某个点作为贝塞尔曲线点


class RobotRealTimeTask(BaseModel):
    # 定义RobotRealTimeTask模型表示实时任务请求模型
    loopTime: int = 1  # 循环次数
    points: List[RobotRealTimePoint] = [RobotRealTimePoint()]  # 实时任务模型任务点列表
    mode: str = ""      # 导航类型，可能值为 "point":多点导航 "path":多路径导航

# actions: Dict[str, RobotTask] = {}


class RobotTaskDict(BaseModel):
    # 定义RobotTaskDict模型表示任务字典
    tasksName: str = "tasks"  # 任务名称
    tasks: Dict[str, RobotTask]  # 任务点列表


"""# 机器人状态相关模块
"""


class RobotStatus(BaseModel):
    """## 定义RobotStatus模型表示机器人状态
    参数：
        - slam: 机器人程序启动状态
            - nav: str 机器人导航状态
                - state: bool 机器人导航状态 ture:开启 false:关闭
                - name: str 机器人导航地图名称，或者当前录制地图名称
                - task: str 机器人当前任务名称
        - robot: 机器人状态
            - angular_velocity: float 机器人角速度
            - linear_velocity: float 机器人线速度
            - fault_code: int 机器人底盘错误信息反馈
            - base_state: int 机器人底盘状态 0:正常状态
            - control_mode: int 机器人底盘控制模式 1-空闲状态 3-手柄控制
        - BMS: 机器人电池状态
            - batteryCurrent: float 机器人电池电流
            - batteryTemperature: float 机器人电池温度
            - batteryVoltage: float 机器人电池电压
            - SOH: int 机器人电池健康状态
            - SOC: int 机器人电池电量
        - sensor: 机器人传感器状态
            - imu_status: str 机器人imu状态：ON/OFF ON:开启 OFF:关闭
            - lidar_status: str 机器人激光雷达状态：ON/OFF ON:开启 OFF:关闭
            - RTK_status: str 机器人RTK状态：ON/OFF ON:开启 OFF:关闭
            - camera_status: str 机器人摄像头状态：ON/OFF ON:开启 OFF:关闭
    """
    slam: Dict[str, dict] = {
        "nav": {"state": False, "name": "", "task": ""}}  # 机器人slam状态
    robot: Dict[str, Union[int, float]] = {
        "angular_velocity": 0.0, "linear_velocity": 0.0, "fault_code": 0, "base_state": 0, "control_mode": 1}  # 机器人状态
    BMS: Dict[str, Union[int, float]] = {
        "batteryCurrent": 0.0, "batteryTemperature": 0.0, "batteryVoltage": 0.0, "SOH": 0, "SOC": 0}  # 机器人电池状态
    sensor: Dict[str, str] = {"imu_status": "ON", "lidar_status": "ON",
                              "RTK_status": "OFF", "camera_status": "OFF"}  # 机器人传感器状态


"""# 机器人上报的日志相关模块
"""


class RobotLog(BaseModel):
    """# 定义RobotLog模型表示机器人上报的日志
    参数：
        - stamp: Dict[str,int] 时间戳
            - sec: int 秒
            - nsec: int 纳秒
        - level: int 日志等级 1:debug 2:info 4:warn 8:error 16:fatal
        - msg: str 日志信息
    """
    stamp: Dict[str, int] = {"sec": 1680848214, "nsec": 679842222}
    level: int = 2
    msg: str = ""


class RobotManage:
    """# 机器人管理类
    """
    ip = "192.168.1.68"  # 设备ip地址
    port = 8880  # 设备端口号
    username = "admin"  # 设备用户名
    password = "dc123456"  # 设备密码

    LastError = -1
    Authorization = ""  # 登录设备返回的用户验证信息，24小时有效
    pose = RobotPose(x=0, y=0, theta=0)
    task = RobotTask()
    tasks: Dict[str, RobotTask] = {task.taskName: task}
    realtime_task = RobotRealTimeTask()
    status = RobotStatus()
    logs: List[RobotLog] = [RobotLog()]

    def __init__(self, ip: str = "192.168.1.68", port: int = 8880, username: str = "admin", password: str = "dc123456"):
        # 初始化机器人管理类
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        # self.Authorization = self.login()
    
    def login(self,base:RobotBase = RobotBase())->bool:
        # 登录设备
        self.ip = base.ip
        self.port = base.port
        self.username = base.username
        self.password = base.password
        return True

    def get_status(self) -> bool:
        # 获取机器人状态信息
        return True

    def get_logs(self) -> bool:
        # 获取机器人日志信息
        return True

    def get_pose(self) -> bool:
        # 获取机器人位置信息
        return True

    def get_task(self) -> bool:
        # 获取机器人任务点信息
        return True

    def get_realtime_task(self) -> bool:
        # 获取机器人实时任务信息
        return True

    def set_pose(self, pose: RobotPose) -> bool:
        # 设置机器人位置信息
        self.pose = pose
        return True

    def set_task(self, task: RobotTask) -> bool:
        # 设置机器人任务点信息
        self.task = task
        return True

    def set_realtime_task(self, realtime_task: RobotRealTimeTask) -> bool:
        # 设置机器人实时任务信息
        self.realtime_task = realtime_task
        return True

    def get_tasks(self) -> Dict[str, RobotTask]:
        # 获取机器人任务列表
        return self.tasks

    def set_tasks(self, tasks: Dict[str, RobotTask]) -> bool:
        # 设置机器人任务列表
        self.tasks = tasks
        return True

    def update_tasks(self, tasks: Dict[str, RobotTask]) -> bool:
        # 更新机器人任务列表
        self.tasks.update(tasks)
        return True

    def add_task(self, task: RobotTask) -> bool:
        # 添加机器人任务
        self.tasks[task.taskName] = task
        return True

    def del_task(self, task_name: str) -> bool:
        # 删除机器人任务
        self.tasks.pop(task_name)
        return True


GRobotManage = RobotManage()

"""END
# 机器人管理模块
"""


"""
机器人管理模块 请求路径与方法
"""

@app.post("/user/robot/login", summary="登录机器人", tags=["机器人管理"])
async def robot_login(base: RobotBase = RobotBase()) -> ResponseReturn:
    """# 登录机器人
    - 参数：
        - base: RobotBase 机器人
            - ip: str 机器人ID
            - port: int 机器人端口号
            - username: str 机器人用户名
            - password: str 机器人密码
        - 示例：{"base":{"ip":"ip","port":port,"username":"username","password":"password"}}
    - 返回：
        - {"base":RobotBase 机器人信息}
    """
    LastError = LastErrorBase()
    if GRobotManage.login(base):
        return ResponseReturn(status=True, code=0, message="Login robot success.", data={"base":base})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.get("/user/robot/status", summary="获取机器人状态相关的信息", tags=["机器人管理"])
async def robot_get_status() -> ResponseReturn:
    """# 获取机器人状态相关的信息
    - 参数：
    - 返回：
        - {"status":RobotStatus 机器人状态信息}
    """
    LastError = LastErrorBase()
    if GRobotManage.get_status():
        return ResponseReturn(status=True, code=0, message="Get robot status success.", data={"status": GRobotManage.status})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.get("/user/robot/pose", summary="获取机器人位置信息", tags=["机器人管理"])
async def robot_get_pose() -> ResponseReturn:
    """# 获取机器人位置信息
        - 参数：
    - 返回：
        - {"pose":RobotPose 机器人位置信息}
    """
    LastError = LastErrorBase()
    if GRobotManage.get_pose():
        return ResponseReturn(status=True, code=0, message="Get robot pose success.", data={"pose": GRobotManage.pose})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/robot/pose", summary="设置机器人位置信息", tags=["机器人管理"])
async def robot_set_pose(pose: RobotPose) -> ResponseReturn:
    """# 设置机器人位置信息
    - 参数：
        - pose: RobotPose 机器人位置信息（必须）
            - x: float 机器人x坐标
            - y: float 机器人y坐标
            - theta: float 机器人角度
    - 示例：
        - {"pose":RobotPose 机器人位置信息}
    """
    LastError = LastErrorBase()
    if GRobotManage.set_pose(pose):
        return ResponseReturn(status=True, code=0, message="Set robot pose success.", data={"pose": GRobotManage.pose})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.get("/user/robot/task", summary="获取地图任务路径信息", tags=["机器人管理"])
async def robot_get_task() -> ResponseReturn:
    """# 获取地图任务路径信息
    - 参数：
    - 返回：
        - {"task":RobotTask 任务信息}
    """
    LastError = LastErrorBase()
    if GRobotManage.get_task():
        return ResponseReturn(status=True, code=0, message="Get robot task success.", data={"task": GRobotManage.task})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/robot/task", summary="设置地图任务路径信息", tags=["机器人管理"])
async def robot_set_task(task: RobotTask) -> ResponseReturn:
    """# 设置地图任务路径信息
    - 参数：
        - RobotTask 任务信息模型
    - 示例：        
        - {"task":{GET方法返回的task的数据}}
    - 返回：
        - {"task":RobotTask 任务信息}
    """
    LastError = LastErrorBase()
    print( task.taskName)
    if GRobotManage.set_task(task):
        return ResponseReturn(status=True, code=0, message="Set robot task success.", data={"task": GRobotManage.task})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.get("/user/robot/tasks", summary="获取所有机器人任务信息", tags=["机器人管理"])
async def robot_get_tasks() -> ResponseReturn:
    """# 获取所有机器人任务路径信息
    - 参数：
    - 返回：
        - {"tasks":Dict[str, RobotTask]}
    """
    LastError = LastErrorBase()
    if GRobotManage.get_tasks():
        return ResponseReturn(status=True, code=0, message="Get robot task list success.", data={"tasks": GRobotManage.tasks})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/robot/tasks", summary="设置机器人所有任务信息", tags=["机器人管理"])
async def robot_set_tasks(tasks: Dict[str, RobotTask]) -> ResponseReturn:
    """# 设置所有机器人实时任务信息
    - 参数：
        - tasks:Dict[str,RobotTask] 任务信息字典

        - 示例：
            {"tasks":Dict[str, RobotTask]}
    - 返回：
        - {"tasks":Dict[str, RobotTask]}
    """
    LastError = LastErrorBase()
    if GRobotManage.set_tasks(tasks):
        return ResponseReturn(status=True, code=0, message="Set robot task slist success.", data={"tasks": GRobotManage.tasks})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/robot/tasks/update", summary="更新机器人任务信息", tags=["机器人管理"])
async def robot_update_tasks(tasks: Dict[str, RobotTask]) -> ResponseReturn:
    """# 更新所有机器人实时任务信息
    - 参数：
        - tasks:Dict[str,RobotTask] 任务信息字典
        - 示例：        
            - {"tasks":Dict[str, RobotTask]}
    - 返回：
        - {"tasks":Dict[str, RobotTask]}
    """
    LastError = LastErrorBase()
    if GRobotManage.update_tasks(tasks):
        return ResponseReturn(status=True, code=0, message="Update robot task list success.", data={"tasks": GRobotManage.tasks})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/robot/tasks/add", summary="添加机器人的一个任务信息", tags=["机器人管理"])
async def robot_add_tasks(task: RobotTask = RobotTask()) -> ResponseReturn:
    """# 添加机器人的一个任务信息
    - 参数：
        - RobotTask 任务信息字典
            - taskName: str 任务名称(必须) 
        - 示例：        
            - {"task": RobotTask }
    - 返回：
        - {"tasks":Dict[str, RobotTask]}
    """
    LastError = LastErrorBase()
    if GRobotManage.add_task(task):
        return ResponseReturn(status=True, code=0, message="Add robot task list success.", data={"tasks": GRobotManage.tasks})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/robot/tasks/delete", summary="删除机器人的一个任务信息", tags=["机器人管理"])
async def robot_delete_tasks(task: RobotTask) -> ResponseReturn:
    """# 删除机器人的一个任务信息
    - 参数：
        - RobotTask 任务信息字典
            - taskName: str 任务名称(必须) 
        - 示例：        
            - {"task": RobotTask} 
    - 返回：
        - {"tasks":Dict[str, RobotTask]}
    """
    LastError = LastErrorBase()
    if GRobotManage.del_task(task.taskName):
        return ResponseReturn(status=True, code=0, message="Delete robot task list success.", data={"tasks": GRobotManage.tasks})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)

"""END
机器人管理模块 请求路径与方法
"""

"""# 传感器管理模块
"""

class SensorBase(BaseModel):
    """传感器基础信息
    - 参数：
        - ip: str 传感器 监听ip地址
        - port: int 传感器 监听端口
        - name: str 传感器名称
        - description: str 传感器描述
    """
    ip: str = "0.0.0.0"
    port: int = 31024
    name: str = "传感器"
    description: str = ""

class SensorData(SensorBase):
    """# 该项目消防机器人传感器数据
    两个氢气，一个烟雾传感器
    - 参数：
        - SensorBase
        - hydrogen1: float 氢气传感器1
        - hydrogen2: float 氢气传感器2
        - smoke: float 烟雾传感器
        - fire: int 是否灭火开关 0:关 1:开（询问时更新）
    """
    hydrogen1: float = 0.0
    hydrogen2: float = 0.0
    smoke: float = 0.0
    fire: int = 0

    
class SensorManage:
    # 传感器信息管理类
    def __init__(self, sensor:SensorData = SensorData()):
        self.sensor = sensor
    def get_data(self) -> bool:
        # 获取传感器数据
        return True

    def set_sensor(self, sensor:SensorData) -> bool:
        # 设置传感器数据
        self.sensor = sensor
        return True
    def set_fire(self, fire:int) -> bool:
        # 设置消防机器人灭火开关
        self.sensor.fire = fire
        return

GSensorManage = SensorManage()
"""END
# 传感器管理模块
"""

"""# 传感器管理模块 请求路径与方法
"""

@app.get("/user/sensor/data", summary="获取传感器数据", tags=["传感器管理"])
async def sensor_get_data(sensor:SensorData = SensorData()) -> ResponseReturn:
    """# 获取传感器数据
    - 参数：
        - SensorData 传感器数据
            - ip: str 传感器 监听ip地址(必须)
            - port: int 传感器 监听端口(必须)
            - 其他参数可选
        - 示例：
            - {"sensor":{"ip":"192.168.1.10","port":41024}}
    - 返回：
        - {"sensor":SensorData}
    """
    LastError = LastErrorBase()
    if GSensorManage.get_data():
        return ResponseReturn(status=True, code=0, message="Get sensor data success.", data={"sensor": GSensorManage.sensor})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)

@app.post("/user/sensor/data", summary="设置传感器数据", tags=["传感器管理"])
async def sensor_set_data(sensor:SensorData = SensorData()) -> ResponseReturn:
    """# 设置传感器数据
    - 参数：
        - SensorData 传感器数据
            - ip: str 传感器 监听ip地址
            - port: int 传感器 监听端口
            - name: str 传感器名称
            - description: str 传感器描述
            - hydrogen1: float 氢气传感器1
            - hydrogen2: float 氢气传感器2
            - smoke: float 烟雾传感器
            - fire: int 是否灭火开关 0:关 1:开（询问时更新）
        - 示例：
            - {"sensor":SensorData}
    - 返回：
        - {"sensor":SensorData}
    """
    LastError = LastErrorBase()
    if GSensorManage.set_sensor(sensor):
        return ResponseReturn(status=True, code=0, message="Set sensor data success.", data={"sensor": GSensorManage.sensor})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)

@app.post("/user/sensor/fire", summary="设置消防机器人灭火开关", tags=["传感器管理"])
async def sensor_set_fire(sensor:SensorData = SensorBase()) -> ResponseReturn:
    """# 设置消防机器人灭火开关
    - 参数：
        - SensorData 传感器数据
            - fire: int 是否灭火开关 0:关 1:开（询问时更新）
            - 其他参数无效
        - 示例：
            - {"sensor":{"fire":0}}
    - 返回：
        - {"sensor":SensorData}
    """
    LastError = LastErrorBase()
    if GSensorManage.set_fire(sensor.fire):
        return ResponseReturn(status=True, code=0, message="Set sensor fire data success.", data={"sensor": GSensorManage.sensor})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)

"""END
# 传感器管理模块 请求路径与方法
"""

class EventBase(BaseModel):
    """事件基础信息
    - 参数：
        - ID: str 事件ID(唯一)(时间戳)
        - name: str 事件名称
        - code: int 事件代码
        - description: str 事件描述
    """
    ID: str = "2023, 7, 6, 18, 17, 2, 557892"
    name: str = ""
    code: int = 0
    description: str = ""


class EventsManage:
    # 事件信息管理类
    events: Dict[str, EventBase] = {}

    def get_events(self) -> bool:
        # 获取所有事件信息
        return True

    def set_events(self, events: Dict[str, EventBase]) -> bool:
        # 设置所有事件信息
        self.events = events
        return True

    def update_events(self, events: Dict[str, EventBase]) -> bool:
        # 更新所有事件信息
        self.events.update(events)
        return True

    def add_event(self, event: EventBase) -> bool:
        # 添加一个事件信息
        self.events[event.ID] = event
        return True

    def del_event(self, event: EventBase) -> bool:
        # 删除一个事件信息
        self.events.pop(event.ID)
        return True

    def get_event(self, event: EventBase) -> EventBase:
        # 获取一个事件信息
        return self.events[event.ID]


GEventsManage = EventsManage()
"""END
# 事件信息管理模块
"""


"""# 事件管理模块 请求路径与方法
"""


@app.get("/user/events", summary="获取所有事件信息", tags=["事件信息管理"])
async def events_get_events() -> ResponseReturn:
    """# 获取所有事件信息
    - 参数：
        - 无
    - 返回：
        - {"events":Dict[str, EventBase]}
    """
    LastError = LastErrorBase()
    if GEventsManage.get_events():
        return ResponseReturn(status=True, code=0, message="Get events list success.", data={"events": GEventsManage.events})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/events", summary="设置所有事件信息", tags=["事件信息管理"])
async def events_set_events(events: Dict[str, EventBase]) -> ResponseReturn:
    """# 设置所有事件信息
    - 参数：
        - events:Dict[str,EventBase] 事件信息字典
        - 示例：        
            - {"events":Dict[str, EventBase]}
    - 返回：
        - {"events":Dict[str, EventBase]}
    """
    LastError = LastErrorBase()
    if GEventsManage.set_events(events):
        return ResponseReturn(status=True, code=0, message="Set events list success.", data={"events": GEventsManage.events})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/events/update", summary="更新事件信息", tags=["事件信息管理"])
async def events_update_events(events: Dict[str, EventBase]) -> ResponseReturn:
    """# 更新所有事件信息
    - 参数：
        - events:Dict[str,EventBase] 事件信息字典
        - 示例：        
            - {"events":Dict[str, EventBase]}
    - 返回：
        - {"events":Dict[str, EventBase]}
    """
    LastError = LastErrorBase()
    if GEventsManage.update_events(events):
        return ResponseReturn(status=True, code=0, message="Update event list success.", data={"events": GEventsManage.events})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/events/add", summary="添加一个事件信息", tags=["事件信息管理"])
async def events_add_event(event: EventBase) -> ResponseReturn:
    """# 添加一个事件信息
    - 参数：
        - EventBase 事件信息字典
            - ID: str 事件ID(唯一)(时间戳)(必须)
            - name: str 事件名称
            - code: int 事件代码 
            - description: str 事件描述 
        - 示例：        
            - {"event":{"ID":"2023, 7, 6, 18, 17, 2, 557892","name":"事件名称","code":0,"description":"事件描述"}}
    - 返回：
        - {"events":Dict[str, EventBase]}
    """
    LastError = LastErrorBase()
    if GEventsManage.add_event(event):
        return ResponseReturn(status=True, code=0, message="Add event list success.", data={"events": GEventsManage.events})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.post("/user/events/del", summary="删除一个事件信息", tags=["事件信息管理"])
async def events_del_event(event: EventBase) -> ResponseReturn:
    """# 删除一个事件信息
    - 参数：
        - EventBase 事件信息字典
            - ID: str 事件ID(唯一)(时间戳)(必须)
        - 示例：        
            - {"event":{"ID":"2023, 7, 6, 18, 17, 2, 557892"}}
    - 返回：
        - {"events":Dict[str, EventBase]}
    """
    LastError = LastErrorBase()
    if GEventsManage.del_event(event.ID):
        return ResponseReturn(status=True, code=0, message="Delete event list success.", data={"events": GEventsManage.events})
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)
"""END
# 事件管理模块 请求路径与方法
"""

"""# 其他 请求路径与方法
"""


@app.get("/", summary="文档", tags=["其他"])
async def root():
    """
    文档说明:readme.md,API参数文档请访问 /docs
    - 无参数
    - 返回：
        - 文档页面
    """
    # return RedirectResponse(url="/docs",status_code=status.HTTP_302_FOUND)
    with open("api.html", encoding='utf-8') as f:
        return HTMLResponse(content=f.read(), status_code=200)


class CommandBase(BaseModel):
    command: str = "start"
    params: Dict[str, dict] = {}


@app.post("other/command", summary="执行用户命令", tags=["其他"])
async def other_command(command: CommandBase) -> ResponseReturn:
    """# **执行用户命令,返回执行结果 DEBUG 的测试模式，仅限测试使用**
    - 参数：
        - command:CommandBase
            - command: str 命令名称(必须)
                - start: 开始
                - stop: 停止
                - pause: 暂停
                - resume: 继续
                - cancel: 取消
                - reboot: 重启
                - shutdown: 关机
            - params: Dict[str, Any] 命令参数
        - 示例：    
            - {"command":"start","params":{}}
    - 返回：    
        - {"status":True,"code":0,"message":"Success","data":{}}
    """
    LastError = LastErrorBase()
    if command.command == "start":
        return ResponseReturn(status=True, code=0, message="Start success.", data={})
    elif command.command == "stop":
        return ResponseReturn(status=True, code=0, message="Stop success.", data={})
    LastError.ERROR_TYPE = "COMMAND_NOT_FOUND"
    LastError.code = 400
    LastError.message = "Command not found."
    return ResponseReturn(status=False, code=-1, message=LastError.message, data=LastError)


@app.get("/other/lasterror", summary="获取最后一次错误信息", tags=["其他"])
async def other_error() -> ResponseReturn:
    """# 获取最后一次错误信息
    - 参数：
        - 无参数
    - 返回：    
        - {"lasterror":LastError}
    """
    return ResponseReturn(status=True, code=0, message="Success", data={"lasterror": GLastError})


"""END
# 其他 请求路径与方法
"""

"""# 发布测试的一些问题
"""
# 以下为权限验证开关
FlagCheckPermission = False
@app.middleware("http")
async def check_authentication(request: Request, call_next):
    def check_permission(method, api, auth):
        # The following paths are always allowed:
        if api == '/login' or api == '/user/login' or api == '/docs' or api == '/' or api == '/openapi.json' or api == '/error':
            return True
        # Parse auth header and check scheme, username and password
        if method == 'POST' or method == 'GET':
            username = GUserManage.get_current_username(auth)
            if username == 'admin':
                return True
            else:
                if method == 'GET':
                    return True
                else:
                    return False
    if FlagCheckPermission:
        auth = request.headers.get('token')
        if not check_permission(request.method, request.url.path, auth):
            return ItemResponseResult(status=False, code=2, message="该用户没有权限，或者token过期", data={})
    return await call_next(request)

# 以下为允许客户端跨域设置
from fastapi.middleware.cors import CORSMiddleware
origins = ["http://localhost","*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],# ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers=["*"],# ["Authorization", "Content-Type", "token"]
)

# 允许HTTPS的证书
from starlette.responses import HTMLResponse
import ssl
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain('cert.pem', 'key.pem')


"""END
# 发布测试的一些问题
"""

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run("run:app", reload=True, port=8000, host="0.0.0.0")
    uvicorn.run("run:app", reload=True, port=8000, host="0.0.0.0",ssl_keyfile="key.pem", ssl_certfile="cert.pem")
