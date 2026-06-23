package demo;

import java.util.regex.*;
public class RegExp_Demo {
	
	
	public static boolean passwordMatche(String pwd,String regex) {
		Pattern pattern = Pattern.compile(regex);
        Matcher matcher = pattern.matcher(pwd);
        return matcher.matches();
	}

	public static void main(String[] args) {

		String password = "IHEP.ihep;2023"; // 用你的密码替换这里
        String regex = "^(?=.{10,})(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*\\W).*$"; //规则 1.至少10个字符  2.包含至少一个大写字母、一个小写字母、一个数字和一个特殊字符
        
        boolean pwdStatus = passwordMatche(password,regex);
        if (pwdStatus) {
            System.out.println("密码符合要求");
        } else {
            System.out.println("密码不符合要求");
        }

	}

}
