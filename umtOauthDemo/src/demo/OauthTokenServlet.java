package demo;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

import cn.vlabs.umt.oauth.AccessToken;
import cn.vlabs.umt.oauth.Oauth;
import cn.vlabs.umt.oauth.UMTOauthConnectException;
import cn.vlabs.umt.oauth.common.exception.OAuthProblemException;


/**
 * 接受重定向code，后台请求UMT OAuth服务器获取用户信息
 * @author zh
 *
 */
public class OauthTokenServlet extends HttpServlet {
	@Override
	protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
		InputStream in = OauthTokenServlet.class.getResourceAsStream("/umtoauthconfig.properties");
		Properties p = new Properties();
		p.load(in);
		Oauth oauth = new Oauth(p);
		System.out.println("jin ru");
		try {
			AccessToken token;
			System.out.println("req :"+req +" code :"+req.getParameter("code"));
			token = oauth.getAccessTokenByRequest(req);
			HttpSession session = req.getSession();
			Object info = session.getAttribute("loginInfo");
			System.out.println("Session"+req.getSession());
			req.setAttribute("token", token.getAccessToken());
			req.setAttribute("refreshToken",token.getRefreshToken());
			//登录完成 获登录的用户信息
			req.setAttribute("userInfo", token.getUserInfo());
			req.getRequestDispatcher("tokenResult.jsp").forward(req, resp);
		} catch (UMTOauthConnectException e) {
			//网络错误
		}catch(OAuthProblemException e){
			//错误码
			String error = e.getError();
			//系统oauth2连接错误
		} 
	}
	@Override
	protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
		doGet(req, resp);
	}

}
