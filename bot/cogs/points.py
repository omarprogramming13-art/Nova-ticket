import discord
from discord.ext import commands
from discord import app_commands
from bot.database.db import db
from bot.utils.embeds import EmbedBuilder
from bot.utils.permissions import PermissionHandler
from typing import Optional

class PointsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="staff_info", description="عرض معلومات وإحصائيات عضو في طاقم الإدارة / View staff performance stats")
    @app_commands.describe(member="العضو المراد عرض إحصائياته (اتركه فارغاً لعرض إحصائياتك)")
    async def staff_info(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        stats = db.get_staff_stats(interaction.guild_id, target.id)
        
        if not stats:
            return await interaction.response.send_message(f"❌ لا توجد بيانات مسجلة لـ {target.mention} في النظام.", ephemeral=True)

        points = stats.get("points", 0)
        tickets = stats.get("tickets_handled", 0)
        total_stars = stats.get("total_stars", 0)
        total_ratings = stats.get("total_ratings", 0)
        avg_rating = round(total_stars / total_ratings, 2) if total_ratings > 0 else 0

        embed = EmbedBuilder.create_embed(
            title=f"📊 إحصائيات الإداري | {target.display_name}",
            description=f"هذه هي الإحصائيات المسجلة لـ {target.mention} في نظام التذاكر.",
            color=EmbedBuilder.COLOR_PRIMARY
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="💰 مجموع النقاط", value=f"**{points}** نقطة", inline=True)
        embed.add_field(name="🎫 تذاكر مستلمة", value=f"**{tickets}** تذكرة", inline=True)
        embed.add_field(name="⭐ متوسط التقييم", value=f"**{avg_rating} / 5** ({total_ratings} تقييم)", inline=True)
        
        # Rankings (optional but cool)
        all_stats = db.get_all_staff_stats(interaction.guild_id)
        rank = "غير مصنف"
        for i, s in enumerate(all_stats):
            if s["user_id"] == target.id:
                rank = f"#{i+1}"
                break
        embed.add_field(name="🏆 الترتيب", value=f"**{rank}** على مستوى الإدارة", inline=True)

        # Staff Achievements & Badges
        badges = []
        if tickets >= 50:
            badges.append("🎖️ **محترف التذاكر** (50+ تذكرة)")
        elif tickets >= 20:
            badges.append("🥉 **منجز الدعم** (20+ تذكرة)")
        elif tickets >= 5:
            badges.append("🔰 **مبادر الدعم** (5+ تذاكر)")

        if points >= 100:
            badges.append("💎 **الماسي** (100+ نقطة)")
        elif points >= 50:
            badges.append("🥇 **الذهبي** (50+ نقطة)")
        elif points >= 20:
            badges.append("🥈 **الفضي** (20+ نقطة)")

        if avg_rating >= 4.8 and total_ratings >= 5:
            badges.append("⭐ **نجم الخدمة الممتازة** (تقييم 4.8+)")
        elif avg_rating >= 4.0 and total_ratings >= 3:
            badges.append("✨ **موظف معتمد** (تقييم 4.0+)")

        if not badges:
            badges.append("⏳ في بداية المشوار لإحراز الأوسمة!")

        embed.add_field(name="🎖️ الأوسمة والإنجازات (Badges):", value="\n".join(badges), inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="staff_leaderboard", description="لوحة صدارة وتصنيف موظفي الدعم الفني / Staff Performance Leaderboard")
    async def staff_leaderboard(self, interaction: discord.Interaction):
        all_stats = db.get_all_staff_stats(interaction.guild_id)
        if not all_stats:
            return await interaction.response.send_message("❌ لا توجد إحصائيات مسجلة للموظفين بعد.", ephemeral=True)

        embed = EmbedBuilder.create_embed(
            title="🏆 لوحة صدارة طاقم الدعم الفني",
            description="ترتيب أفضل الموظفين حسب النقاط والتذاكر المنجزة:",
            color=EmbedBuilder.COLOR_PRIMARY
        )

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for idx, s in enumerate(all_stats[:10]):
            medal = medals[idx] if idx < 3 else f"`#{idx+1}`"
            u_id = s.get("user_id")
            pts = s.get("points", 0)
            t_cnt = s.get("tickets_handled", 0)
            t_stars = s.get("total_stars", 0)
            t_ratings = s.get("total_ratings", 0)
            avg = round(t_stars / t_ratings, 1) if t_ratings > 0 else 0.0

            lines.append(
                f"{medal} <@{u_id}> — **{pts}** نقطة | **{t_cnt}** تذكرة | ⭐ **{avg}** ({t_ratings})"
            )

        embed.add_field(name="📊 أفضل الموظفين:", value="\n".join(lines), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="points_add", description="إضافة نقاط لعضو في طاقم الإدارة / Add points to a staff member")
    @app_commands.describe(member="العضو المراد إضافة النقاط له", points="عدد النقاط")
    async def points_add(self, interaction: discord.Interaction, member: discord.Member, points: int):
        if not PermissionHandler.is_admin(interaction.user):
            return await interaction.response.send_message("❌ هذا الأمر مخصص للإدارة العليا فقط.", ephemeral=True)
        
        db.update_staff_points(interaction.guild_id, member.id, points)
        await interaction.response.send_message(f"✅ تم إضافة **{points}** نقطة لـ {member.mention} بنجاح.")

    @app_commands.command(name="points_remove", description="خصم نقاط من عضو في طاقم الإدارة / Remove points from a staff member")
    @app_commands.describe(member="العضو المراد خصم النقاط منه", points="عدد النقاط")
    async def points_remove(self, interaction: discord.Interaction, member: discord.Member, points: int):
        if not PermissionHandler.is_admin(interaction.user):
            return await interaction.response.send_message("❌ هذا الأمر مخصص للإدارة العليا فقط.", ephemeral=True)
        
        db.update_staff_points(interaction.guild_id, member.id, -points)
        await interaction.response.send_message(f"✅ تم خصم **{points}** نقطة من {member.mention} بنجاح.")

    @app_commands.command(name="points_reset", description="تصفير نقاط عضو أو جميع طاقم الإدارة / Reset points for one or all staff")
    @app_commands.describe(member="العضو المراد تصفير نقاطه (اتركه فارغاً لتصفير نقاط الجميع)")
    async def points_reset(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        if not PermissionHandler.is_admin(interaction.user):
            return await interaction.response.send_message("❌ هذا الأمر مخصص للإدارة العليا فقط.", ephemeral=True)
        
        if member:
            db.reset_staff_points(interaction.guild_id, member.id)
            await interaction.response.send_message(f"✅ تم تصفير نقاط {member.mention} بنجاح.")
        else:
            db.reset_staff_points(interaction.guild_id)
            await interaction.response.send_message("✅ تم تصفير نقاط جميع أعضاء طاقم الإدارة بنجاح.")

    # Prefix Commands
    @commands.command(name="اضافة")
    async def prefix_add_points(self, ctx: commands.Context, member: discord.Member, points: int):
        if not PermissionHandler.is_admin(ctx.author):
            return await ctx.send("❌ هذا الأمر مخصص للإدارة العليا فقط.")
        
        db.update_staff_points(ctx.guild.id, member.id, points)
        await ctx.send(f"✅ تم إضافة **{points}** نقطة لـ {member.mention} بنجاح.")

    @commands.command(name="خصم")
    async def prefix_remove_points(self, ctx: commands.Context, member: discord.Member, points: int):
        if not PermissionHandler.is_admin(ctx.author):
            return await ctx.send("❌ هذا الأمر مخصص للإدارة العليا فقط.")
        
        db.update_staff_points(ctx.guild.id, member.id, -points)
        await ctx.send(f"✅ تم خصم **{points}** نقطة من {member.mention} بنجاح.")

async def setup(bot: commands.Bot):
    await bot.add_cog(PointsCog(bot))
