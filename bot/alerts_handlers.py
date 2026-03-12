from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_user, create_price_alert, get_user_alerts, delete_alert

router = Router()

SUPPORTED_SYMBOLS = ["BTC", "ETH", "SOL"]

class AlertSetup(StatesGroup):
    waiting_symbol = State()
    waiting_condition = State()
    waiting_price = State()

# ─── /alerte ─────────────────────────────────────────────────────

@router.message(Command("alerte"))
async def cmd_alerte(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    await state.update_data(language=lang)

    builder = InlineKeyboardBuilder()
    for symbol in SUPPORTED_SYMBOLS:
        builder.button(text=f"🪙 {symbol}", callback_data=f"alert_symbol:{symbol}")
    builder.adjust(3)

    texts = {
        "fr": "🔔 *Nouvelle alerte de prix*\n\nSur quelle crypto veux-tu une alerte ?",
        "en": "🔔 *New price alert*\n\nWhich crypto do you want an alert on?",
        "es": "🔔 *Nueva alerta de precio*\n\n¿En qué cripto quieres una alerta?",
        "pt": "🔔 *Novo alerta de preço*\n\nEm qual cripto você quer um alerta?",
    }
    await message.answer(
        texts.get(lang, texts["fr"]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(AlertSetup.waiting_symbol)

@router.callback_query(AlertSetup.waiting_symbol, F.data.startswith("alert_symbol:"))
async def cb_alert_symbol(callback: CallbackQuery, state: FSMContext):
    symbol = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("language", "fr")

    await state.update_data(symbol=symbol)

    builder = InlineKeyboardBuilder()
    labels = {
        "fr": [("📈 Au-dessus de", "above"), ("📉 En-dessous de", "below")],
        "en": [("📈 Above", "above"), ("📉 Below", "below")],
        "es": [("📈 Por encima de", "above"), ("📉 Por debajo de", "below")],
        "pt": [("📈 Acima de", "above"), ("📉 Abaixo de", "below")],
    }
    for text, data_val in labels.get(lang, labels["fr"]):
        builder.button(text=text, callback_data=f"alert_condition:{data_val}")
    builder.adjust(2)

    texts = {
        "fr": f"🪙 *{symbol}* sélectionné.\n\nCondition de l'alerte :",
        "en": f"🪙 *{symbol}* selected.\n\nAlert condition:",
        "es": f"🪙 *{symbol}* seleccionado.\n\nCondición de la alerta:",
        "pt": f"🪙 *{symbol}* selecionado.\n\nCondição do alerta:",
    }
    await callback.message.edit_text(
        texts.get(lang, texts["fr"]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(AlertSetup.waiting_condition)
    await callback.answer()

@router.callback_query(AlertSetup.waiting_condition, F.data.startswith("alert_condition:"))
async def cb_alert_condition(callback: CallbackQuery, state: FSMContext):
    condition = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("language", "fr")
    symbol = data.get("symbol")

    await state.update_data(condition=condition)

    direction = {
        "fr": "au-dessus de" if condition == "above" else "en-dessous de",
        "en": "above" if condition == "above" else "below",
        "es": "por encima de" if condition == "above" else "por debajo de",
        "pt": "acima de" if condition == "above" else "abaixo de",
    }

    texts = {
        "fr": f"📊 Alerte quand *{symbol}* passe *{direction['fr']}*...\n\nEnvoie le prix cible en $ _(ex: 75000)_ :",
        "en": f"📊 Alert when *{symbol}* goes *{direction['en']}*...\n\nSend the target price in $ _(e.g. 75000)_ :",
        "es": f"📊 Alerta cuando *{symbol}* pase *{direction['es']}*...\n\nEnvía el precio objetivo en $ _(ej: 75000)_ :",
        "pt": f"📊 Alerta quando *{symbol}* passar *{direction['pt']}*...\n\nEnvie o preço alvo em $ _(ex: 75000)_ :",
    }
    await callback.message.edit_text(
        texts.get(lang, texts["fr"]),
        parse_mode="Markdown"
    )
    await state.set_state(AlertSetup.waiting_price)
    await callback.answer()

@router.message(AlertSetup.waiting_price)
async def process_alert_price(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "fr")
    symbol = data.get("symbol")
    condition = data.get("condition")

    try:
        price = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        errors = {
            "fr": "❌ Prix invalide. Envoie un nombre comme *75000* ou *2500.50*",
            "en": "❌ Invalid price. Send a number like *75000* or *2500.50*",
            "es": "❌ Precio inválido. Envía un número como *75000* o *2500.50*",
            "pt": "❌ Preço inválido. Envie um número como *75000* ou *2500.50*",
        }
        await message.answer(errors.get(lang, errors["fr"]), parse_mode="Markdown")
        return

    user_id = message.from_user.id
    await create_price_alert(user_id, symbol, condition, price)

    direction = {
        "fr": "passe au-dessus de" if condition == "above" else "passe en-dessous de",
        "en": "goes above" if condition == "above" else "goes below",
        "es": "supere" if condition == "above" else "caiga por debajo de",
        "pt": "subir acima de" if condition == "above" else "cair abaixo de",
    }

    success = {
        "fr": (
            f"✅ *Alerte créée !*\n\n"
            f"🪙 {symbol} {direction['fr']} *${price:,.0f}*\n"
            f"🔔 Tu seras notifié dès que le prix atteint cet objectif.\n\n"
            f"Gère tes alertes avec /alertes"
        ),
        "en": (
            f"✅ *Alert created!*\n\n"
            f"🪙 {symbol} {direction['en']} *${price:,.0f}*\n"
            f"🔔 You'll be notified when the price hits this target.\n\n"
            f"Manage your alerts with /alertes"
        ),
        "es": (
            f"✅ *¡Alerta creada!*\n\n"
            f"🪙 {symbol} {direction['es']} *${price:,.0f}*\n"
            f"🔔 Te notificaremos cuando el precio alcance este objetivo.\n\n"
            f"Gestiona tus alertas con /alertes"
        ),
        "pt": (
            f"✅ *Alerta criado!*\n\n"
            f"🪙 {symbol} {direction['pt']} *${price:,.0f}*\n"
            f"🔔 Você será notificado quando o preço atingir este alvo.\n\n"
            f"Gerencie seus alertas com /alertes"
        ),
    }

    await state.clear()
    await message.answer(success.get(lang, success["fr"]), parse_mode="Markdown")

# ─── /alertes ────────────────────────────────────────────────────

@router.message(Command("alertes"))
async def cmd_alertes(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    alerts = await get_user_alerts(user_id)

    if not alerts:
        empty = {
            "fr": "🔕 Aucune alerte active.\n\nCrée une alerte avec /alerte",
            "en": "🔕 No active alerts.\n\nCreate one with /alerte",
            "es": "🔕 No hay alertas activas.\n\nCrea una con /alerte",
            "pt": "🔕 Nenhum alerta ativo.\n\nCrie um com /alerte",
        }
        await message.answer(empty.get(lang, empty["fr"]))
        return

    titles = {
        "fr": f"🔔 *Tes alertes actives* ({len(alerts)})\n\n",
        "en": f"🔔 *Your active alerts* ({len(alerts)})\n\n",
        "es": f"🔔 *Tus alertas activas* ({len(alerts)})\n\n",
        "pt": f"🔔 *Seus alertas ativos* ({len(alerts)})\n\n",
    }

    builder = InlineKeyboardBuilder()
    lines = [titles.get(lang, titles["fr"])]

    condition_labels = {
        "above": "📈 >",
        "below": "📉 <",
    }

    for alert in alerts:
        cond = condition_labels[alert["condition"]]
        lines.append(f"🪙 *{alert['symbol']}* {cond} ${float(alert['target_price']):,.0f}")
        builder.button(
            text=f"🗑 {alert['symbol']} {cond} ${float(alert['target_price']):,.0f}",
            callback_data=f"alert_delete:{alert['id']}"
        )

    builder.adjust(1)
    await message.answer(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("alert_delete:"))
async def cb_alert_delete(callback: CallbackQuery):
    alert_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    deleted = await delete_alert(alert_id, user_id)

    texts_ok = {
        "fr": "✅ Alerte supprimée.",
        "en": "✅ Alert deleted.",
        "es": "✅ Alerta eliminada.",
        "pt": "✅ Alerta excluído.",
    }
    texts_ko = {
        "fr": "❌ Alerte introuvable.",
        "en": "❌ Alert not found.",
        "es": "❌ Alerta no encontrada.",
        "pt": "❌ Alerta não encontrado.",
    }

    texts = texts_ok if deleted else texts_ko
    await callback.answer(texts.get(lang, texts["fr"]), show_alert=True)
    await callback.message.delete()
