import os, uuid, json, requests
from flask import Flask, request

TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_ID=int(os.environ["ADMIN_TELEGRAM_ID"])
PDF_FILE_ID=os.environ.get("TELEGRAM_PDF_FILE_ID","")
API=f"https://api.telegram.org/bot{TOKEN}"
PRICE=399
orders={}
app=Flask(__name__)

def tg(method, **kwargs):
    return requests.post(f"{API}/{method}", data=kwargs, timeout=30).json()

def send(chat_id,text,**kwargs):
    return tg("sendMessage",chat_id=chat_id,text=text,**kwargs)

def handle(u):
    if "message" in u:
        m=u["message"]; cid=m["chat"]["id"]
        if "document" in m and cid==ADMIN_ID:
            send(cid,"PDF received. Your Telegram file ID is:\n\n"+m["document"]["file_id"])
            return
        t=m.get("text","").strip()
        if t.startswith("/start"):
            send(cid,"📚 Zema Books",reply_markup=json.dumps({"inline_keyboard":[[{"text":"📚 Browse Books","callback_data":"books"}]]})); return
        if t.startswith("/approve ") and cid==ADMIN_ID:
            oid=t.split(maxsplit=1)[1]; o=orders.get(oid)
            if not o: send(cid,"Order not found."); return
            if not PDF_FILE_ID: send(cid,"PDF not configured yet. Send the PDF to this bot, then add its file ID in Render."); return
            tg("sendDocument",chat_id=o["user_id"],document=PDF_FILE_ID,caption="✅ Payment confirmed!\n\n📕 Psychology\nThank you for your purchase.")
            o["status"]="delivered"; send(cid,f"✅ {oid} approved and PDF delivered."); return
        if t.startswith("/reject ") and cid==ADMIN_ID:
            orders.pop(t.split(maxsplit=1)[1],None); send(cid,"❌ Order rejected."); return
        for oid,o in orders.items():
            if o["user_id"]==cid and o["status"]=="awaiting_payment" and t:
                o["status"]="pending_admin"
                send(cid,f"📨 Payment reference received.\nOrder: {oid}\n\nWe are checking your payment.")
                send(ADMIN_ID,f"💰 NEW PAYMENT\n\nOrder: {oid}\nBook: Psychology\nAmount: {PRICE} ETB\nPayment reference: {t}\n\nApprove: /approve {oid}\nReject: /reject {oid}")
                return
    if "callback_query" in u:
        q=u["callback_query"]; tg("answerCallbackQuery",callback_query_id=q["id"])
        cid=q["message"]["chat"]["id"]; d=q["data"]
        if d=="books":
            tg("editMessageText",chat_id=cid,message_id=q["message"]["message_id"],text="📚 Available Books\n\n📕 Psychology — 399 ETB",reply_markup=json.dumps({"inline_keyboard":[[{"text":"📕 Psychology — 399 ETB","callback_data":"buy"}]]}))
        elif d=="buy":
            oid="ZEMA-"+uuid.uuid4().hex[:8].upper(); orders[oid]={"user_id":cid,"status":"awaiting_payment"}
            tg("editMessageText",chat_id=cid,message_id=q["message"]["message_id"],text=f"📕 Psychology\n💰 399 ETB\n🧾 Order: {oid}\n\nChoose payment:",reply_markup=json.dumps({"inline_keyboard":[[{"text":"📱 Pay with Telebirr","callback_data":"pay"}]]}))
        elif d=="pay":
            oid=next((k for k,v in orders.items() if v["user_id"]==cid and v["status"]=="awaiting_payment"),"unknown")
            details=os.environ.get("TELEBIRR_PAYMENT_DETAILS","ADD YOUR TELEBIRR PAYMENT DETAILS")
            send(cid,f"🧾 Order: {oid}\n💰 399 ETB\n\n📱 Pay with Telebirr:\n{details}\n\nAfter paying, send your transaction/reference number here.")

@app.post("/telegram")
def webhook(): handle(request.get_json(silent=True) or {}); return "ok"
@app.get("/")
def health(): return "Zema Books Bot is running."
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT","10000")))
