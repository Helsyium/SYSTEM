# Sabit değerler ve konfigürasyon

# Uygulama genelinde kullanılacak sabit tuz (Salt).
# BÜYÜK NOT: Gerçek bir üretim ortamında bu değer 
# uygulama ilk kurulduğunda rastgele üretilip bir dosyada saklanmalıdır.
# Ancak bu proje kapsamında taşınabilirlik ve basitlik için sabitliyoruz.
GLOBAL_VAULT_SALT = b'\xd1\x8a\x02\x9f\x18\x2a\x7c\x44\x91\xe2\x04\xae\xbc\xdd\xfe\x99'

APP_NAME = "Antigravity Vault"
ENCRYPTED_EXT = ".agv" # Antigravity Vault
