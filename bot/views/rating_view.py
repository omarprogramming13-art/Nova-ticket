import discord
from discord.ui import View, Button, Modal, TextInput
from bot.database.db import db
from bot.config.locales import get_text
from bot.utils.embeds import EmbedBuilder

class FeedbackModal(Modal):
    def __init__(self, ticket_id: int, staff_id: int, stars: int, lang: str = "ar"):
        super().__init__(title="⭐ إضافة تعليق وتقييم الموظف")
        self.ticket_id = ticket_id
        self.staff_id = staff_id
        self.stars = stars
        self.lang = lang

        self.comment = TextInput(
            label="ملاحظاتك أو تعليقك على الخدمة (اختياري)",
            placeholder="كيف كانت تجربتك مع الموظف المستلم؟",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )
        self.add_item(self.comment)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if db.has_ticket_been_rated(self.ticket_id):
                if interaction.message:
                    try:
                        await interaction.message.delete()
                    except Exception:
                        pass
                return await interaction.response.send_message("❌ لقد قمت بتقييم هذه التذكرة بالفعل!", ephemeral=True)

            feedback_text = self.comment.value.strip() if self.comment.value else "بدون تعليق"
            db.add_rating(
                ticket_id=self.ticket_id,
                user_id=interaction.user.id,
                staff_id=self.staff_id,
                stars=self.stars,
                feedback=feedback_text
            )

            guild_id = interaction.guild_id
            ticket = db.get_ticket_by_id(self.ticket_id)
            if not guild_id and ticket:
                guild_id = ticket.get("guild_id")

            # Calculate points tied to rating stars
            # 5 stars = +15 pts, 4 stars = +10 pts, 3 stars = +5 pts, 2 stars = 0 pts, 1 star = -5 pts
            points_map = {5: 15, 4: 10, 3: 5, 2: 0, 1: -5}
            awarded_points = points_map.get(self.stars, 5)

            if guild_id and self.staff_id:
                db.update_staff_points(guild_id, self.staff_id, awarded_points)
                db.add_staff_rating_stat(guild_id, self.staff_id, self.stars)

            # Log review in log_channel if configured, especially with alert if low rating
            if guild_id:
                guild_obj = interaction.guild or (interaction.client.get_guild(guild_id) if hasattr(interaction, "client") else None)
                if guild_obj:
                    settings = db.get_guild_settings(guild_id) or {}
                    log_ch_id = settings.get("log_channel_id")
                    if log_ch_id:
                        log_ch = guild_obj.get_channel(int(log_ch_id))
                        if log_ch:
                            star_symbols = "⭐" * self.stars
                            review_color = EmbedBuilder.COLOR_DANGER if self.stars <= 2 else (EmbedBuilder.COLOR_WARNING if self.stars == 3 else EmbedBuilder.COLOR_SUCCESS)
                            alert_prefix = "⚠️ [تنبيه تقييم منخفض] " if self.stars <= 2 else "⭐ [تقييم جديد] "
                            review_embed = EmbedBuilder.create_embed(
                                title=f"{alert_prefix}تقييم خدمة الدعم الفني",
                                description=f"تم استلام تقييم جديد للتذكرة رقم `#{self.ticket_id}`",
                                color=review_color
                            )
                            review_embed.add_field(name="👤 العميل", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
                            review_embed.add_field(name="👔 الموظف المسؤول", value=f"<@{self.staff_id}> (`{self.staff_id}`)", inline=True)
                            review_embed.add_field(name="⭐ النجوم", value=f"**{self.stars}/5** ({star_symbols})", inline=True)
                            review_embed.add_field(name="💬 ملاحظة / تعليق العميل", value=f"```{feedback_text}```", inline=False)
                            review_embed.add_field(name="💰 النقاط المستحقة", value=f"`{'+' if awarded_points >= 0 else ''}{awarded_points}` نقطة", inline=True)
                            try:
                                await log_ch.send(embed=review_embed)
                            except Exception as ch_err:
                                print(f"Could not send review embed to log channel: {ch_err}")

            # Try deleting the original rating request message (with the 5 star buttons)
            if interaction.message:
                try:
                    await interaction.message.delete()
                except Exception as del_err:
                    print(f"Could not delete rating prompt message: {del_err}")

            thank_you_embed = EmbedBuilder.create_embed(
                title="⭐ شكراً جزيلاً لتقييمك!",
                description=(
                    f"مرحباً {interaction.user.mention} 👋،\n"
                    f"تم تسجيل تقييمك بنجاح بـ **`{self.stars}/5 ★`**.\n\n"
                    f"شكراً لوقتك وملاحظاتك القيمة لتطوير مستوى خدمة الدعم الفني! ❤️"
                ),
                color=EmbedBuilder.COLOR_SUCCESS
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=thank_you_embed, ephemeral=False)
            else:
                await interaction.followup.send(embed=thank_you_embed, ephemeral=False)
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ حدث خطأ أثناء حفظ التقييم: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ حدث خطأ أثناء حفظ التقييم: {e}", ephemeral=True)


class RatingView(View):
    def __init__(self, ticket_id: int, staff_id: int, lang: str = "ar"):
        super().__init__(timeout=86400)
        self.ticket_id = ticket_id
        self.staff_id = staff_id
        self.lang = lang

        for star in range(1, 6):
            btn = Button(
                label=f"{star} ⭐",
                style=discord.ButtonStyle.secondary if star < 4 else discord.ButtonStyle.success,
                custom_id=f"rate_{star}_{ticket_id}"
            )
            btn.callback = self.make_callback(star)
            self.add_item(btn)

    def make_callback(self, stars: int):
        async def callback(interaction: discord.Interaction):
            if db.has_ticket_been_rated(self.ticket_id):
                if interaction.message:
                    try:
                        await interaction.message.delete()
                    except Exception:
                        pass
                return await interaction.response.send_message("❌ لقد قمت بتقييم هذه التذكرة بالفعل!", ephemeral=True)
            
            modal = FeedbackModal(ticket_id=self.ticket_id, staff_id=self.staff_id, stars=stars, lang=self.lang)
            await interaction.response.send_modal(modal)
        return callback


