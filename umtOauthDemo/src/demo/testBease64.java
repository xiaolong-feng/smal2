package demo;

import java.io.UnsupportedEncodingException;
import java.util.Base64;

public class testBease64 {

	public static void main(String[] args) throws UnsupportedEncodingException {
		// TODO Auto-generated method stub
		 Base64.Decoder decoder = Base64.getDecoder();
		 Base64.Encoder encoder = Base64.getEncoder();
		 String text = "mykeystr";
		 byte[] srcByte = text.getBytes("UTF-8");
		//编码
		 String encodedText = encoder.encodeToString(srcByte);
		System.out.println(encodedText);
		//解码
		System.out.println(new String(decoder.decode(encodedText), "UTF-8"));


	}

}
