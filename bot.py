import os
import uuid
from flask import Flask, request
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_TELEGRAM_ID"])
PDF_FILE_ID = os.environ["TELEGRAM_PDF_FILE_ID"]
API = f"https://api.telegram.org/bot{TOKEN}"
PRICE = 399
orders = {}
app = Flask(__name__)

def tg(method, **kwargs):
    return requests.post(f"{API}/{method}", data=kwargs, timeout=30).json()

def send(chat_id, text, **kwargs):
    return tg("sendMessage", chat_id=chat_id, text=text, **kwargs)

def start(chat_id):
    kb = {"inline_keyboard":[[{"text":"📚 Browse Books","callback_data":"books"}]]}
    send(chat_id, "📚 Zema Books\n\nDigital books delivered directly in Telegram.",
         reply_markup=__import__("json").dumps(kb))

def handle(update):
    if "message" in update:
        m=update["message"]; chat_id=m["chat"]["id"]; text=m.get("text","").strip()

        if text.startswith("/start"):
            start(chat_id); return

        if text.startswith("/approve ") and chat_id == ADMIN_ID:
            oid=text.split(maxsplit=1)[1]
            order=orders.get(oid)
            if not order:
                send(chat_id,"Order not found."); return
            tg("sendDocument", chat_id=order["user_id"], document=PDF_FILE_ID,
               caption="✅ Payment confirmed!\n\n📕 Psychology\nThank you for your purchase.")
            order["status"]="delivered"
            send(chat_id,f"✅ {oid} approved and PDF delivered.")
            return

        if text.startswith("/reject ") and chat_id == ADMIN_ID:
            oid=text.split(maxsplit=1)[1]
            orders.pop(oid,None)
            send(chat_id,f"❌ {oid} rejected.")
            return

        for oid,order in orders.items():
            if order["user_id"]==chat_id and order["status"]=="awaiting_payment" and text:
                order["payment_ref"]=text
                order["status"]="pending_admin"
                send(chat_id,f"📨 Payment reference received.\nOrder: {oid}\n\nWe are checking your payment.")
                send(ADMIN_ID,
                     f"💰 NEW PAYMENT\n\nOrder: {oid}\nBook: Psychology\nAmount: {PRICE} ETB\n"
                     f"Customer ID: {chat_id}\nPayment reference: {text}\n\n"
                     f"Approve: /approve {oid}\nReject: /reject {oid}")
                return

    if "callback_query" in update:
        q=update["callback_query"]
        tg("answerCallbackQuery",callback_query_id=q["id"])
        chat_id=q["message"]["chat"]["id"]; data=q["data"]; import json

        if data=="books":
            kb={"inline_keyboard":[[{"text":"📕 Psychology — 399 ETB","callback_data":"buy"}]]}
            tg("editMessageText",chat_id=chat_id,message_id=q["message"]["message_id"],
               text="📚 Available Books\n\n📕 Psychology — 399 ETB",
               reply_markup=json.dumps(kb))

        elif data=="buy":
            oid="ZEMA-"+uuid.uuid4().hex[:8].upper()
            orders[oid]={"user_id":chat_id,"status":"awaiting_payment"}
            kb={"inline_keyboard":[[{"text":"📱 Pay with Telebirr","callback_data":"pay"}]]}
            tg("editMessageText",chat_id=chat_id,message_id=q["message"]["message_id"],
               text=f"📕 Psychology\n💰 399 ETB\n🧾 Order: {oid}\n\nChoose payment:",
               reply_markup=json.dumps(kb))

        elif data=="pay":
            details=os.environ.get("TELEBIRR_PAYMENT_DETAILS","ADD YOUR TELEBIRR PAYMENT DETAILS")
            oid=next((k for k,v in orders.items()
                      if v["user_id"]==chat_id and v["status"]=="awaiting_payment"),"unknown")
            send(chat_id,
                 f"🧾 Order: {oid}\n💰 399 ETB\n\n📱 Pay with Telebirr:\n{details}\n\n"
                 "After paying, send your Telebirr transaction/reference number here.")

@app.post("/telegram")
def telegram():
    handle(request.get_json(silent=True) or {})
    return "ok"

@app.get("/")
def health():
    return "Zema Books Bot is running."

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","10000")))
