import discord
from discord.ext import commands
from discord import app_commands
from bot.database.db import db
from bot.utils.embeds import EmbedBuilder

class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ticket_stats", description="View ticket system statistics / إحصائيات وتقارير التذاكر المتقدمة")
    async def ticket_stats(self, interaction: discord.Interaction):
        stats = db.get_statistics()
        
        embed = EmbedBuilder.create_embed(
            title="📊 تقرير وأداء نظام التذاكر (Ticket System Analytics)",
            description="نظرة شاملة ودقيقة على حركة التذاكر، سرعة الاستجابة، وتقييم أداء الطاقم الإداري.",
            color=EmbedBuilder.COLOR_PRIMARY
        )
        embed.add_field(name="🎫 إجمالي التذاكر", value=f"**{stats['total_tickets']}** تذكرة", inline=True)
        embed.add_field(name="🟢 تذاكر مفتوحة حالياً", value=f"**{stats['open_tickets']}**", inline=True)
        embed.add_field(name="🔴 تذاكر مغلقة ومنجزة", value=f"**{stats['closed_tickets']}**", inline=True)
        
        # Performance metrics
        avg_resp = stats.get("avg_response_minutes", 0.0)
        avg_resp_str = f"**{avg_resp}** دقيقة" if avg_resp > 0 else "غير محدد بعد"
        embed.add_field(name="⚡ متوسط سرعة أول رد", value=avg_resp_str, inline=True)

        avg_res = stats.get("avg_resolution_hours", 0.0)
        avg_res_str = f"**{avg_res}** ساعة" if avg_res > 0 else "غير محدد بعد"
        embed.add_field(name="⏳ متوسط مدة إنهاء التذكرة", value=avg_res_str, inline=True)

        embed.add_field(name="⭐ متوسط تقييم العملاء", value=f"**{stats['average_rating']} / 5.0**", inline=True)

        # Priority breakdown
        p_breakdown = stats.get("priority_breakdown", {})
        if p_breakdown:
            p_lines = [f"• **{k}:** `{v}` تذكرة" for k, v in p_breakdown.items() if k]
            if p_lines:
                embed.add_field(name="⚡ تصنيف الأولويات:", value="\n".join(p_lines[:5]), inline=False)

        top_staff_str = ""
        for s in stats["top_staff"]:
            user_mention = f"<@{s['staff_id']}>"
            top_staff_str += f"• {user_mention}: {round(s['avg_stars'], 2)} ⭐ ({s['total_ratings']} تقييم)\n"

        if top_staff_str:
            embed.add_field(name="🏆 أفضل موظفي الدعم الفني:", value=top_staff_str, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="view_ratings", description="View staff ratings / عرض تقييمات الموظفين")
    @app_commands.describe(staff="The staff member to view ratings for")
    async def view_ratings(self, interaction: discord.Interaction, staff: discord.Member = None):
        if staff:
            ratings = db.get_staff_ratings(staff.id)
            title = f"⭐ تقييمات {staff.display_name}"
        else:
            ratings = db.get_all_ratings(limit=10)
            title = "⭐ أحدث التقييمات العامة"

        if not ratings:
            return await interaction.response.send_message("❌ لا توجد تقييمات مسجلة حالياً.", ephemeral=True)

        embed = EmbedBuilder.create_embed(title=title, description="قائمة بأحدث تقييمات طاقم الدعم الفني:", color=EmbedBuilder.COLOR_WARNING)
        for r in ratings[:10]:
            staff_mention = f"<@{r['staff_id']}>"
            user_mention = f"<@{r['user_id']}>"
            feedback = r['feedback'] or "بدون تعليق"
            rating_id = r.get("id")
            embed.add_field(
                name=f"Rating #{rating_id} by {user_mention}",
                value=f"• **Staff:** {staff_mention}\n• **Stars:** {'⭐' * r['stars']}\n• **Feedback:** {feedback}\n• **Date:** {str(r['created_at'])[:10]}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="delete_rating", description="Delete a specific rating by ID / حذف تقييم محدد برقم التقييم")
    @app_commands.describe(rating_id="رقم التقييم المراد حذفه")
    async def delete_rating(self, interaction: discord.Interaction, rating_id: int):
        from bot.utils.permissions import PermissionHandler
        if not PermissionHandler.is_staff(interaction.user):
            return await interaction.response.send_message("❌ ليس لديك صلاحية لحذف التقييمات.", ephemeral=True)
            
        db.delete_rating(rating_id)
        await interaction.response.send_message(f"✅ تم حذف التقييم رقم #{rating_id} بنجاح.", ephemeral=True)

    @app_commands.command(name="delete_user_rating", description="Delete rating from a specific user for a specific staff / حذف تقييم عضو لإداري معين")
    @app_commands.describe(member="العضو صاحب التقييم", staff="الموظف/الإداري المقيّم")
    async def delete_user_rating(self, interaction: discord.Interaction, member: discord.Member, staff: discord.Member):
        from bot.utils.permissions import PermissionHandler
        if not PermissionHandler.is_staff(interaction.user):
            return await interaction.response.send_message("❌ ليس لديك صلاحية لحذف التقييمات.", ephemeral=True)

        guild_id = interaction.guild_id or 0
        deleted_count = db.delete_rating_by_user_and_staff(member.id, staff.id, guild_id)
        if deleted_count > 0:
            await interaction.response.send_message(f"✅ تم حذف {deleted_count} تقييم مقدم من {member.mention} للإداري {staff.mention} بنجاح.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ لم يتم العثور على أي تقييم مقدم من {member.mention} للإداري {staff.mention}.", ephemeral=True)

    @app_commands.command(name="clear_ratings", description="Clear staff ratings / مسح تقييمات موظف")
    @app_commands.describe(staff="The staff member to clear ratings for (leave empty for all)")
    async def clear_ratings(self, interaction: discord.Interaction, staff: discord.Member = None):
        from bot.utils.permissions import PermissionHandler
        rank = PermissionHandler.get_member_rank(interaction.user)
        if rank < PermissionHandler.ROLE_HIERARCHY["admin"]:
            return await interaction.response.send_message("❌ يتطلب هذا الأمر صلاحية (Admin) أو أعلى.", ephemeral=True)

        if staff:
            db.delete_staff_ratings(staff.id)
            await interaction.response.send_message(f"✅ تم مسح جميع تقييمات {staff.mention} بنجاح.")
        else:
            db.delete_all_ratings()
            await interaction.response.send_message("✅ تم مسح جميع التقييمات في النظام بنجاح.")

async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
