<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>NOVA Conversation History</title>
<style>
body{font:16px system-ui,sans-serif;background:#101522;color:#edf2ff;margin:0;padding:40px}main{max-width:850px;margin:auto}h1{color:#8fb7ff}.entry{background:#1b2435;border:1px solid #34415a;border-radius:12px;padding:16px;margin:12px 0}.meta{color:#9eabc2;font-size:13px;margin-bottom:8px}.message{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#8fb7ff}
</style></head><body><main>
<h1>NOVA Conversation History</h1><p>Most recent 200 messages · <a href="${pageContext.request.contextPath}/">Back to NOVA history service</a></p>
<c:choose><c:when test="${empty entries}"><p>No saved conversations yet. Start NOVA and have a conversation.</p></c:when><c:otherwise>
<c:forEach var="entry" items="${entries}"><article class="entry"><div class="meta"><c:out value="${entry.speaker}"/> · <c:out value="${entry.createdAt}"/></div><div class="message"><c:out value="${entry.message}"/></div></article></c:forEach>
</c:otherwise></c:choose></main></body></html>
