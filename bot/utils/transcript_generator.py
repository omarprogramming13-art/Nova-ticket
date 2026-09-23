import os
import html
from typing import List
import discord

class TranscriptGenerator:
    @staticmethod
    async def generate_html(channel: discord.TextChannel, ticket_info: dict = None) -> str:
        messages: List[discord.Message] = []
        async for msg in channel.history(limit=1000, oldest_first=True):
            messages.append(msg)

        ticket_id = ticket_info.get("id", channel.name) if ticket_info else channel.name
        user_name = ticket_info.get("user_id", "Unknown User") if ticket_info else "User"
        priority_label = ticket_info.get("priority", "عادية") if ticket_info else "عادية"
        dept_label = ticket_info.get("department", "عام") if ticket_info else "عام"
        claimed_by_id = ticket_info.get("claimed_by") if ticket_info else None
        claimed_str = f"<span class='meta-tag'>الموظف: <@{claimed_by_id}></span>" if claimed_by_id else "<span class='meta-tag'>غير مستلمة</span>"

        messages_html = ""
        for m in messages:
            author_name = html.escape(m.author.display_name)
            avatar_url = m.author.display_avatar.url
            timestamp = m.created_at.strftime("%Y-%m-%d %I:%M %p UTC")
            content = html.escape(m.content) if m.content else ""
            bot_badge = '<span class="bot-badge">BOT</span>' if m.author.bot else ""

            # Attachments
            attachments_html = ""
            for att in m.attachments:
                if att.content_type and "image" in att.content_type:
                    attachments_html += f'<div class="attachment"><a href="{att.url}" target="_blank"><img src="{att.url}" alt="image" style="max-width:420px; max-height:300px; border-radius:8px; margin-top:8px; border:1px solid #3f4147;" /></a></div>'
                else:
                    attachments_html += f'<div class="attachment" style="margin-top:6px;"><a href="{att.url}" target="_blank" style="display:inline-flex; align-items:center; gap:6px; background:#2b2d31; padding:8px 12px; border-radius:6px; color:#5865f2; text-decoration:none; font-weight:500; border:1px solid #3f4147;">📎 {html.escape(att.filename)}</a></div>'

            # Embeds
            embeds_html = ""
            for emb in m.embeds:
                emb_title = html.escape(emb.title) if emb.title else ""
                emb_desc = html.escape(emb.description) if emb.description else ""
                emb_color = f"{emb.color.value:06x}" if emb.color else "5865f2"
                fields_html = ""
                if emb.fields:
                    for f in emb.fields:
                        fields_html += f'<div style="margin-top:6px;"><strong style="color:#ffffff;">{html.escape(f.name)}:</strong> <div style="color:#dbdee1;">{html.escape(f.value)}</div></div>'

                embeds_html += f'''
                <div class="embed-box" style="border-left: 4px solid #{emb_color};">
                    {f'<div class="embed-title">{emb_title}</div>' if emb_title else ''}
                    {f'<div class="embed-desc">{emb_desc}</div>' if emb_desc else ''}
                    {fields_html}
                </div>
                '''

            messages_html += f'''
            <div class="chat-message">
                <img class="avatar" src="{avatar_url}" alt="avatar" />
                <div class="message-body">
                    <div class="message-header">
                        <span class="author">{author_name}</span> {bot_badge}
                        <span class="timestamp">{timestamp}</span>
                    </div>
                    {f'<div class="content">{content}</div>' if content else ''}
                    {embeds_html}
                    {attachments_html}
                </div>
            </div>
            '''

        html_template = f'''<!DOCTYPE html>
<html lang="ar" dir="auto">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أرشيف التذكرة #{ticket_id} | {channel.name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            background-color: #1e1f22;
            color: #dbdee1;
            font-family: 'Cairo', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 24px;
        }}
        .header-bar {{
            background: linear-gradient(135deg, #2b2d31 0%, #232428 100%);
            padding: 24px;
            border-radius: 14px;
            margin-bottom: 24px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.35);
            border: 1px solid #35373c;
        }}
        .header-title {{
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
            margin: 0 0 12px 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .header-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            font-size: 13px;
        }}
        .meta-tag {{
            background-color: #313338;
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #3f4147;
            color: #f2f3f5;
        }}
        .chat-container {{
            background-color: #2b2d31;
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25);
            border: 1px solid #35373c;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}
        .chat-message {{
            display: flex;
            gap: 16px;
            padding: 10px 14px;
            border-radius: 10px;
            transition: background 0.15s ease;
        }}
        .chat-message:hover {{
            background-color: #313338;
        }}
        .avatar {{
            width: 44px;
            height: 44px;
            border-radius: 50%;
            object-fit: cover;
            flex-shrink: 0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }}
        .message-body {{
            display: flex;
            flex-direction: column;
            flex: 1;
            overflow: hidden;
        }}
        .message-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 5px;
        }}
        .author {{
            font-weight: 700;
            color: #ffffff;
            font-size: 15px;
        }}
        .bot-badge {{
            background-color: #5865f2;
            color: #ffffff;
            font-size: 10px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
            letter-spacing: 0.5px;
        }}
        .timestamp {{
            font-size: 12px;
            color: #949ba4;
        }}
        .content {{
            font-size: 15px;
            line-height: 1.5;
            color: #dbdee1;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .embed-box {{
            background-color: #232428;
            padding: 14px 16px;
            border-radius: 8px;
            margin-top: 8px;
            max-width: 600px;
            border: 1px solid #35373c;
        }}
        .embed-title {{
            font-weight: 700;
            color: #ffffff;
            font-size: 15px;
            margin-bottom: 6px;
        }}
        .embed-desc {{
            font-size: 14px;
            color: #b5bac1;
            line-height: 1.4;
            white-space: pre-wrap;
        }}
        .footer-note {{
            margin-top: 30px;
            text-align: center;
            font-size: 13px;
            color: #80848e;
            padding: 14px;
        }}
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="header-title">🎫 سجل وأرشيف التذكرة #{ticket_id}</div>
        <div class="header-meta">
            <span class="meta-tag">قناة: #{channel.name}</span>
            <span class="meta-tag">الأولوية: {priority_label}</span>
            <span class="meta-tag">القسم: {dept_label}</span>
            <span class="meta-tag">الرسائل: {len(messages)}</span>
            <span class="meta-tag">تاريخ الحفظ: {discord.utils.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</span>
        </div>
    </div>
    <div class="chat-container">
        {messages_html if messages_html else '<div style="text-align:center; padding:30px; color:#949ba4;">لا توجد رسائل مسجلة في هذه التذكرة.</div>'}
    </div>
    <div class="footer-note">
        نظام التذاكر المتقدم © تم إنشاء وحفظ نسخة الأرشيف آلياً
    </div>
</body>
</html>'''
        return html_template
        return html_template

    @staticmethod
    async def send_transcript(channel: discord.TextChannel, ticket: dict, guild: discord.Guild, interaction: discord.Interaction = None):
        html_content = await TranscriptGenerator.generate_html(channel, ticket)
        file_name = f"transcript-{channel.name}.html"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(html_content)

        file = discord.File(file_name, filename=file_name)

        if interaction:
            try:
                if interaction.response.is_done():
                    await interaction.followup.send("📄 **Ticket Transcript Generated:**", file=file)
                else:
                    await interaction.response.send_message("📄 **Ticket Transcript Generated:**", file=file, ephemeral=True)
            except Exception:
                try:
                    await channel.send("📄 **Ticket Transcript Generated:**", file=file)
                except Exception:
                    pass
        else:
            try:
                await channel.send("📄 **Ticket Transcript Generated:**", file=file)
            except Exception:
                pass

        try:
            from bot.database.db import db
            settings = db.get_guild_settings(guild.id) or {}
            trans_ch_id = settings.get("transcript_channel_id")
            if trans_ch_id:
                trans_ch = guild.get_channel(trans_ch_id)
                if not trans_ch:
                    try:
                        trans_ch = await guild.fetch_channel(trans_ch_id)
                    except Exception:
                        trans_ch = None
                
                if trans_ch:
                    from bot.utils.embeds import EmbedBuilder
                    ticket_id = ticket.get("id", "N/A") if ticket else "N/A"
                    user_id = ticket.get("user_id") if ticket else None
                    user_mention = f"<@{user_id}>" if user_id else "غير معروف"
                    embed = EmbedBuilder.create_embed(
                        title=f"📄 أرشيف تذكرة جديدة #{ticket_id}",
                        description=f"• **اسم القناة:** `#{channel.name}`\n• **صاحب التذكرة:** {user_mention}\n• **الحالة:** أرشيف محادثة HTML",
                        color=EmbedBuilder.COLOR_INFO
                    )
                    file_for_trans = discord.File(file_name, filename=file_name)
                    await trans_ch.send(embed=embed, file=file_for_trans)
        except Exception as e:
            print(f"Error sending transcript to transcript_channel: {e}")

        if os.path.exists(file_name):
            try:
                os.remove(file_name)
            except Exception:
                pass

