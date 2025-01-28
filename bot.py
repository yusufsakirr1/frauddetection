import requests
from datetime import datetime


# DexScreener API'sinden token bilgilerini çekme
def get_dex_data(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "API'ye erişim sağlanamadı."}


# Solscan API'sinden token'ın kilitli yüzdesini çekme
def get_locked_percentage_solscan(token_address):
    try:
        # Solscan API'si üzerinden token bilgilerini çekme
        url = f"https://api.solscan.io/token/{token_address}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Token'ın toplam arzı ve dolaşımdaki arzı
            total_supply = float(data.get("data", {}).get("totalSupply", 0))
            circulating_supply = float(data.get("data", {}).get("circulatingSupply", 0))

            if total_supply > 0:
                locked_percentage = ((total_supply - circulating_supply) / total_supply) * 100
                return locked_percentage
            else:
                return None
        else:
            return None
    except Exception as e:
        print(f"Solscan API'sinden veri çekme hatası: {e}")
        return None


# Token dağılımını analiz etme
def analyze_token_distribution(data):
    if "error" in data:
        return data["error"]

    pairs = data.get("pairs", [])
    if not pairs:
        return "Token'a ait pair bulunamadı."

    # İlk pair'i analiz et (genellikle en likit pair)
    pair = pairs[0]
    base_token = pair.get("baseToken", {})
    total_supply = float(base_token.get("totalSupply", 0))

    if total_supply <= 0:
        return "Token'ın toplam arzı bulunamadı veya geçersiz."

    # Likidite sağlayıcılarının cüzdan adreslerini çekme
    lp_holders = pair.get("liquidityProviderHolders", [])
    if not lp_holders:
        return "Likidite sağlayıcılarına ait bilgi bulunamadı."

    # İlk 5 cüzdanın token yüzdesini hesapla
    top_holders = []
    for holder in lp_holders[:5]:  # İlk 5 cüzdanı al
        address = holder.get("address", "Bilinmeyen Cüzdan")
        balance = float(holder.get("balance", 0))
        percentage = (balance / total_supply) * 100
        top_holders.append({"address": address, "percentage": percentage})

    return {
        "total_supply": total_supply,
        "top_holders": top_holders
    }


# Token bilgilerini analiz ederek scam riskini hesaplama
def analyze_token(data, token_address):
    if "error" in data:
        return data["error"]

    pairs = data.get("pairs", [])
    if not pairs:
        return "Token'a ait pair bulunamadı."

    # İlk pair'i analiz et (genellikle en likit pair)
    pair = pairs[0]
    liquidity = float(pair.get("liquidity", {}).get("usd", 0))
    volume = float(pair.get("volume", {}).get("h24", 0))
    fdv = float(pair.get("fdv", 0))
    created_at = pair.get("pairCreatedAt", None)
    social_media = pair.get("info", {}).get("socials", [])  # Sosyal medya bilgileri

    # Risk puanı ve açıklamalar
    risk_score = 0
    explanations = []

    # 1. Likidite Analizi
    if liquidity < 10000:  # Likidite < $10,000
        risk_score += 3
        explanations.append("🔴 Likidite çok düşük (< $10,000). Bu, token'ın manipüle edilmesini kolaylaştırır.")
    elif liquidity < 50000:  # Likidite < $50,000
        risk_score += 2
        explanations.append("🟡 Likidite düşük (< $50,000). Dikkatli olun.")
    else:
        explanations.append("🟢 Likidite yeterli (> $50,000). Bu, token'ın daha güvenilir olduğunu gösterir.")

    # 2. İşlem Hacmi Analizi
    if volume < 1000:  # Hacim < $1,000
        risk_score += 2
        explanations.append("🔴 İşlem hacmi çok düşük (< $1,000). Token'ın ilgi görmediğini gösterir.")
    elif volume < 10000:  # Hacim < $10,000
        risk_score += 1
        explanations.append("🟡 İşlem hacmi düşük (< $10,000). Daha fazla araştırma yapın.")
    else:
        explanations.append("🟢 İşlem hacmi yeterli (> $10,000). Token aktif bir şekilde işlem görüyor.")

    # 3. FDV (Fully Diluted Valuation) Analizi
    if fdv > 1000000 and liquidity < 100000:  # FDV > $1M ve Likidite < $100,000
        risk_score += 2
        explanations.append(
            "🔴 FDV çok yüksek (> $1M) ve likidite düşük. Bu, token'ın aşırı değerlenmiş olabileceğini gösterir.")
    elif fdv > 500000:  # FDV > $500,000
        risk_score += 1
        explanations.append("🟡 FDV yüksek (> $500,000). Dikkatli olun.")
    else:
        explanations.append("🟢 FDV makul seviyede. Token'ın değeri gerçekçi görünüyor.")

    # 4. Token Yaşı Analizi
    if created_at:
        created_time = datetime.fromtimestamp(created_at / 1000)
        current_time = datetime.now()
        age = (current_time - created_time).days
        if age < 7:  # Token 7 günden daha yeni
            risk_score += 3
            explanations.append("🔴 Token çok yeni (< 7 gün). Yeni token'lar yüksek risk taşır.")
        elif age < 30:  # Token 30 günden daha yeni
            risk_score += 1
            explanations.append("🟡 Token nispeten yeni (< 30 gün). Dikkatli olun.")
        else:
            explanations.append("🟢 Token eski (> 30 gün). Bu, token'ın daha güvenilir olduğunu gösterir.")

    # 5. Kilitli Token Yüzdesi (Solscan API'sinden çek)
    locked_percentage = get_locked_percentage_solscan(token_address)
    if locked_percentage is not None:
        if locked_percentage < 20:  # Kilitli yüzde < %20
            risk_score += 2
            explanations.append(
                "🔴 Kilitli token yüzdesi çok düşük (< %20). Bu, token'ın manipüle edilmesini kolaylaştırır.")
        elif locked_percentage < 50:  # Kilitli yüzde < %50
            risk_score += 1
            explanations.append("🟡 Kilitli token yüzdesi düşük (< %50). Dikkatli olun.")
        else:
            explanations.append(
                "🟢 Kilitli token yüzdesi yeterli (> %50). Bu, token'ın daha güvenilir olduğunu gösterir.")
    else:
        explanations.append("🟡 Kilitli token yüzdesi bilgisi bulunamadı. Solscan API'si üzerinden çekilemedi.")

    # 6. Sosyal Medya Hesapları
    if not social_media:
        risk_score += 2
        explanations.append("🔴 Sosyal medya hesapları bulunamadı. Bu, projenin şeffaf olmadığını gösterir.")
    else:
        explanations.append("🟢 Sosyal medya hesapları mevcut. Bu, projenin şeffaf olduğunu gösterir.")

    # 7. Token Dağılımı Analizi
    distribution_result = analyze_token_distribution(data)
    if isinstance(distribution_result, str):  # Hata mesajı döndüyse
        explanations.append(f"🟡 Token dağılım analizi: {distribution_result}")
    else:
        top_holders = distribution_result["top_holders"]
        explanations.append("🟢 Token dağılım analizi:")
        for holder in top_holders:
            explanations.append(f"- {holder['address']}: {holder['percentage']:.2f}%")

        # İlk cüzdanın yüzdesi %50'den fazla ise riskli olarak işaretle
        if top_holders and top_holders[0]["percentage"] > 50:
            risk_score += 3
            explanations.append("🔴 Token'ın %50'den fazlası tek bir cüzdanda toplanmış. Bu, yüksek risk taşır.")

    # Risk puanını 10 üzerinden hesapla
    risk_score = min(risk_score, 10)  # Maksimum risk puanı 10

    # Sonuç raporu oluştur
    result = {
        "risk_score": risk_score,
        "explanations": explanations
    }
    return result


# Ana fonksiyon
def main():
    print("DexScreener Scam Botu'na hoş geldiniz!")
    token_address = input("Lütfen token adresini girin: ")

    # Token bilgilerini çek
    data = get_dex_data(token_address)

    # Scam analizi yap
    result = analyze_token(data, token_address)

    # Sonucu ekrana yazdır
    print("\nAnaliz Sonucu:")
    print(f"Risk Puanı: {result['risk_score']}/10")
    print("\nAçıklamalar:")
    for explanation in result["explanations"]:
        print(f"- {explanation}")


# Programı çalıştır
if __name__ == "__main__":
    main()