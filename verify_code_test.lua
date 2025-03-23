-- 设置方法、路径、头信息和请求体
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

-- 生成随机电子邮件
local counter = 0
local function random_email()
    counter = counter + 1
    return string.format("testuser%d@example.com", counter)
end

-- 请求初始化函数
function setup(thread)
    -- 线程初始化
end

-- 每个请求调用此函数
function request()
    local email = random_email()
    local body = '{"email":"' .. email .. '"}'
    return wrk.format(nil, nil, nil, body)
end

-- 处理响应的函数
function response(status, headers, body)
    -- 这里不处理响应
end