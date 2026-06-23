package demo;

import java.util.Base64;

//import sun.misc.BASE64Decoder;
//import sun.misc.BASE64Encoder;





import javax.crypto.Cipher;

import javax.crypto.SecretKeyFactory;

import javax.crypto.spec.DESedeKeySpec;

import javax.crypto.spec.IvParameterSpec;

import java.security.Key;


public class des3EncodeCBC {
	
	
	
	/**

	* @param key 密钥

	* @param keyiv IV

	* @param data 明文

	* @return Base64编码的密文

	* @throws Exception

	* @Description CBC加密

	*/

	public static byte[] Des3EncodeCBC(byte[] key, String keyiv, byte[] data) throws Exception {
	Key deskey = null;

	DESedeKeySpec spec = new DESedeKeySpec(key);

	SecretKeyFactory keyfactory = SecretKeyFactory.getInstance("desede");

	deskey = keyfactory.generateSecret(spec);

	Cipher cipher = Cipher.getInstance("desede" + "/CBC/PKCS5Padding");

	IvParameterSpec ips = new IvParameterSpec(keyiv.getBytes());

	cipher.init(Cipher.ENCRYPT_MODE, deskey, ips);

	byte[] bOut = cipher.doFinal(data);

	return bOut;

	}

	/**

	* @param key 密钥

	* @param keyiv IV

	* @param data Base64编码的密文

	* @return 明文

	* @throws Exception

	* @Description CBC解密

	*/

	public static byte[] des3DecodeCBC(byte[] key, String keyiv, byte[] data) throws Exception {
	Key deskey = null;

	DESedeKeySpec spec = new DESedeKeySpec(key);

	SecretKeyFactory keyfactory = SecretKeyFactory.getInstance("desede");

	deskey = keyfactory.generateSecret(spec);

	Cipher cipher = Cipher.getInstance("desede" + "/CBC/PKCS5Padding");

	IvParameterSpec ips = new IvParameterSpec(keyiv.getBytes());

	cipher.init(Cipher.DECRYPT_MODE, deskey, ips);

	byte[] bOut = cipher.doFinal(data);

	return bOut;

	}


	public static void main(String[] args) throws Exception {
		//byte[] key = new BASE64Decoder().decodeBuffer("YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4");
		String src = "mykeystr";
		final Base64.Decoder decoder = Base64.getDecoder();
		
		byte[] srcByte = src.getBytes("UTF-8");
		byte[] key = Base64.getEncoder().encode(srcByte);
		System.out.println(key.length);

		//byte[] keyiv = {1, 2, 3, 4, 5, 6, 7, 8};
		String keyiv = "24680";

		byte[] data = "myumtpassword".getBytes("UTF-8");

		System.out.println("CBC加密解密");
		System.out.println(src.getBytes().length);

		byte[] str5 = Des3EncodeCBC(key, keyiv, data);

		byte[] str6 = des3DecodeCBC(key, keyiv, str5);
		
		System.out.println(new String(decoder.decode(str5), "UTF-8"));

		//System.out.println(new BASE64Encoder().encode(str5));

		System.out.println(new String(str6, "UTF-8"));

		String str7 = "uHrew7Thp2taL2NJpSJhF2mdFMP7BZ1W";

		//byte[] str8 = new BASE64Decoder().decodeBuffer(str7);

		//byte[] str9 = des3DecodeCBC(key, keyiv, str8);

		//System.out.println(new String(str9, "UTF-8"));

		}}


