package demo;

import java.io.IOException;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import cn.vlabs.umt.oauth.Oauth;
import cn.vlabs.umt.oauth.UMTOauthConnectException;
/**
 * 获取应用登录地址
 * @author zh
 * 
 */
public class UmtOAuthAddressServlet extends HttpServlet {
	protected void doGet(HttpServletRequest request, HttpServletResponse response)
			throws ServletException, IOException {
		try {
			Oauth oauth = new Oauth("umtoauthconfig.properties");
			response.sendRedirect(oauth.getAuthorizeURL(request));
		} catch (UMTOauthConnectException e) {
			e.printStackTrace();
		}
	}
}
