# 一个简单的pytest+CICD+Docker自动测试平台
## pyTets
 - 阶梯or常规压测注册、登录接口
 - 直接从redis里拿验证码
 - wrk压测验证码接口
## Docker
 - Dockerfile封装压力测试环境
 - 部署时用docker-compose.yml编排容器
## CI/CD
 - 高度可复用的基于docker-image的Github Actions脚本
 - 先构建镜像，构建完推送到ghrc
 - 自动ssh连接到服务器，通过docker-compose up -d直接拉起更新的实例
