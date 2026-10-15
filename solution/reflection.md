# Reflection

## Nhung loai loi kho phat hien nhat

Cac loi co bien do nho la kho nhat: do lech phan phoi, training-serving skew,
embedding drift va do tre van co the nam trong khoang baseline mean +/- 3 sigma.
Baseline tinh giup han che bao dong gia nhung khong bao phu het cac loi nay.
Practice dat TPR 100%, FPR 0%, diem 50/50; private dat TPR 62.96%, FPR 0%,
diem 31.48/50. Ket qua cho thay practice khong dai dien day du cho loi tinh vi.
Khong thay doi detector theo ket qua private.

Lineage can phan biet inputs khai bao va upstream thuc te: danh sach khai bao
co the khong day du. Toi kiem tra inputs bat buoc, so output, runtime va hoc
topology pho bien theo job tu cac su kien da nhan. Cach nay khong can answer
key, nhung co han che cold start va co the bao nham khi topology thay doi hop le.

## Danh doi chi phi va do bao phu

Moi su kien dung mot toolkit call dung loai, khong goi lap. Practice tieu thu
180/220 credits; private khong vuot ngan sach. Detector chi dung payload,
ctx.tools, ctx.baseline va ctx.state; khong doc file hay hardcode event ID.
Loi API duoc xu ly thanh ket qua khong du du lieu, khong lam crash handler.

Neu co them mot lan phat trien, toi se danh gia robust median/MAD theo nhom
va ket hop nhieu tin hieu yeu de bat loi duoi nguong. Can warm-up, gioi han
anh huong cua outlier va kiem thu tren du lieu validation doc lap truoc khi
ha nguong. Toi cung se tach canh bao monitoring bi loi khoi canh bao du lieu,
va ho tro topology version de tranh bao dong gia khi pipeline duoc cap nhat.
