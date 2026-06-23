<%@ page language="java" contentType="text/html; charset=utf-8"
    pageEncoding="utf-8"%>
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>Insert title here</title>
</head>
<body>
	用户登录成功！
	<table>
		<tr>
			<td>用户名称</td>
			<td>${userInfo.trueName }</td>
		</tr>
		<tr>
			<td>用户邮箱</td>
			<td>${userInfo.cstnetId }</td>
		</tr>
		<tr>
			<td>用户umt id</td>
			<td>${userInfo.umtId }</td>
		</tr>
		<tr>
			<td>用户类型</td>
			<td>${userInfo.type} </td>
		</tr>
		<tr>
			<td>用户登录类型</td>
			<td>${userInfo.passwordType }</td>
		</tr>
		<tr>
			<td>token</td>
			<td>${token}</td>
		</tr>
		<tr>
			<td>refresh token</td>
			<td>${refreshToken }</td>
		</tr>
	
	</table>
<br/>
<!-- WebServerURL的值为退出中国科技网登录后的重定向地址 -->
<a href="http://passport.escience.cn/logout?WebServerURL=http%3A%2F%2F127.0.0.1%3A8080%2FumtOauthDemo%2F">退出中国科技网登录</a>
</body>
</html>