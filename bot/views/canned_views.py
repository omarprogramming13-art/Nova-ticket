import discord
from discord.ui import View, Select, Button, Modal, TextInput
from typing import List, Dict, Any, Optional
from bot.database.db import db
from bot.utils.embeds import EmbedBuilder
from bot.utils.permissions import PermissionHandler

class SendCannedModal(Modal):
    def __init__(self, title_text: str, content_text: str):
        super().__init__(title=f"💬 إرسال رد سريع: {title_text[:20]}")
        self.msg_input = TextInput(
            label="نص الرد (يمكنك تعديله قبل الإرسال)",
            style=discord.TextStyle.paragraph,
            default=content_text,
            required=True,
            max_length=2000
        )
        self.add_item(self.msg_input)

    async def on_submit(self, interaction: discord.Interaction):
        text = self.msg_input.value.strip()
        embed = discord.Embed(
            description=text,
            color=EmbedBuilder.COLOR_PRIMARY
        )
        embed.set_author(name=f"رد من طاقم الدعم: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
        embed.set_footer(text="💬 رد سريع معتمد • Discord Ticket Support")
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ **تم إرسال الرد السريع في التذكرة بنجاح!**", ephemeral=True)


class CannedResponseSelectView(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        responses = db.get_canned_responses(guild_id)
        
        options = []
        for r in responses[:25]:
            desc = r.get("content", "")[:95]
            options.append(discord.SelectOption(
                label=r.get("title", "رد سريع")[:50],
                value=str(r.get("id")),
                description=desc,
                emoji="💬"
            ))

        if not options:
            options.append(discord.SelectOption(label="لا توجد ردود جاهزة", value="none", emoji="⚠️"))

        select = Select(placeholder="💬 اختر رداً جاهزاً لإرساله فوراً...", options=options, min_values=1, max_values=1)
        select.callback = self.on_select
        self.add_item(select)

        b_manage = Button(label="⚙️ إدارة الردود الجاهزة", style=discord.ButtonStyle.secondary, emoji="⚙️", row=1)
        async def manage_cb(i: discord.Interaction):
            if not PermissionHandler.is_staff(i.user) and not PermissionHandler.is_bot_owner(i.user.id):
                return await i.response.send_message("❌ هذا الخيار مخصص لطاقم الدعم الفني فقط.", ephemeral=True)
            v = ManageCannedResponsesView(self.guild_id)
            await i.response.send_message(embed=v.build_embed(), view=v, ephemeral=True)
        b_manage.callback = manage_cb
        self.add_item(b_manage)

    async def on_select(self, interaction: discord.Interaction):
        val = interaction.data["values"][0]
        if val == "none":
            return await interaction.response.send_message("⚠️ لا توجد ردود جاهزة حالياً.", ephemeral=True)

        responses = db.get_canned_responses(self.guild_id)
        chosen = next((r for r in responses if str(r.get("id")) == val), None)
        if not chosen:
            return await interaction.response.send_message("❌ لم يتم العثور على هذا الرد.", ephemeral=True)

        # Open modal allowing staff to review/edit or send directly
        await interaction.response.send_modal(SendCannedModal(chosen.get("title", ""), chosen.get("content", "")))


class AddCannedModal(Modal):
    def __init__(self, guild_id: int):
        super().__init__(title="➕ إضافة رد سريع جديد")
        self.guild_id = guild_id

        self.shortcut_input = TextInput(label="الاختصار (Shortcut)", placeholder="مثال: معلومات_الحساب", required=True, max_length=30)
        self.title_input = TextInput(label="عنوان الرد", placeholder="مثال: طلب صورة وتفاصيل المشكلة", required=True, max_length=50)
        self.content_input = TextInput(label="نص الرد الكامل", placeholder="أدخل نص الرد الجاهز الذي سيصل للعضو...", style=discord.TextStyle.paragraph, required=True, max_length=1500)

        self.add_item(self.shortcut_input)
        self.add_item(self.title_input)
        self.add_item(self.content_input)

    async def on_submit(self, interaction: discord.Interaction):
        sc = self.shortcut_input.value.strip().replace(" ", "_")
        ti = self.title_input.value.strip()
        co = self.content_input.value.strip()

        db.add_canned_response(self.guild_id, sc, ti, co, interaction.user.id)
        await interaction.response.send_message(f"✅ **تمت إضافة الرد السريع `{ti}` بنجاح!**", ephemeral=True)


class ManageCannedResponsesView(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.refresh_items()

    def refresh_items(self):
        self.clear_items()
        responses = db.get_canned_responses(self.guild_id)

        if responses:
            options = []
            for r in responses[:25]:
                options.append(discord.SelectOption(
                    label=r.get("title", "رد")[:50],
                    value=str(r.get("id")),
                    description=f"اختصار: {r.get('shortcut', '')}"[:100],
                    emoji="🗑️"
                ))
            del_select = Select(placeholder="🗑️ اختر رداً سريعاً لحذفه نهائياً...", options=options, min_values=1, max_values=1)
            async def del_cb(i: discord.Interaction):
                r_id = int(i.data["values"][0])
                db.delete_canned_response(r_id, self.guild_id)
                self.refresh_items()
                await i.response.edit_message(embed=self.build_embed(), view=self)
            del_select.callback = del_cb
            self.add_item(del_select)

        b_add = Button(label="➕ إضافة رد سريع جديد", style=discord.ButtonStyle.success, emoji="➕", row=1)
        async def add_cb(i: discord.Interaction):
            await i.response.send_modal(AddCannedModal(self.guild_id))
        b_add.callback = add_cb
        self.add_item(b_add)

    def build_embed(self) -> discord.Embed:
        responses = db.get_canned_responses(self.guild_id)
        lines = []
        for idx, r in enumerate(responses, 1):
            lines.append(f"**{idx}. {r.get('title')}** `[/{r.get('shortcut')}]`\n↳ {r.get('content')[:120]}...")
        desc = "\n\n".join(lines) if lines else "لا توجد ردود سريعة مسجلة حالياً."

        embed = discord.Embed(
            title="💬 إدارة الردود السريعة الجاهزة (Canned Responses)",
            description=desc,
            color=EmbedBuilder.COLOR_PRIMARY
        )
        embed.set_footer(text="يمكنك استخدام القائمة لحذف رد، أو الزر لإضافة رد جديد.")
        return embed
