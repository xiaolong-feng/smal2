package demo;

import java.util.Base64;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class testAEs {
	
	private static final String key = "UmtKeyEncryptStr";
	private static final String initVector = "StrKeyUmtIVvalue";
	 
	public static String encrypt(String value) {
		try {
			Base64.Encoder encoder = Base64.getEncoder();
			IvParameterSpec iv = new IvParameterSpec(initVector.getBytes("UTF-8"));
			SecretKeySpec skeySpec = new SecretKeySpec(key.getBytes("UTF-8"), "AES");
	 
			Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5PADDING");
			cipher.init(Cipher.ENCRYPT_MODE, skeySpec, iv);
	 
			byte[] encrypted = cipher.doFinal(value.getBytes());
			return encoder.encodeToString(encrypted);
			//return Base64.encodeBase64String(encrypted);
		} catch (Exception ex) {
			ex.printStackTrace();
		}
		return null;
	}
	
	public static String decrypt(String encrypted) {
		try {
			Base64.Decoder decoder = Base64.getDecoder();
			IvParameterSpec iv = new IvParameterSpec(initVector.getBytes("UTF-8"));
			SecretKeySpec skeySpec = new SecretKeySpec(key.getBytes("UTF-8"), "AES");
	 
			Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5PADDING");
			cipher.init(Cipher.DECRYPT_MODE, skeySpec, iv);
			byte[] original = cipher.doFinal(decoder.decode(encrypted));
			//byte[] original = cipher.doFinal(Base64.decodeBase64(encrypted));
			
	 
			return new String(original);
		} catch (Exception ex) {
			ex.printStackTrace();
		}
	 
		return null;
	}

	public static void main(String[] args) {
		// TODO Auto-generated method stub
		String originalString = "myumtpassword";
		System.out.println("Original String to encrypt - " + originalString);
		String encryptedString = encrypt(originalString);
		System.out.println("Encrypted String - " + encryptedString);
		String decryptedString = decrypt(encryptedString);
		System.out.println("After decryption - " + decryptedString);

	}

}
