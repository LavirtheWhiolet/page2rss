#!/usr/bin/env ruby
require 'cgi'
require 'open-uri'
require 'digest'

class Object
  
  # @return [String, Object] self or +value+'s result.
  def if_nil_or_empty(&value)
    if self.nil? or (self.is_a? String and self.empty?) then value.() else self end
  end
  
  alias or2 if_nil_or_empty
  
end

# @param [String] uri
# @param [Hash] options see {OpenURI}.
# @yieldparam [IO] io
# @raise Exception
def open_uri_safe(uri, options = {}, &f)
  uri = URI.encode(URI.decode(uri))
  uri = URI(uri)
  raise 'URI is invalid' unless ["http", "https", "ftp"].include? uri.scheme
  io = uri.open(options)
  begin
    f.(io)
  ensure
    io.close
  end
end

# Default value of how often the tracked page is accessed.
DEFAULT_TTL = "60"

begin
  cgi = CGI.new
  # Parse request (1).
  uri = cgi["uri"].or2 { nil }
  if uri then
    # Parse request (2).
    ttl = cgi["ttl"].or2 { DEFAULT_TTL }
    title = cgi["title"].or2 { uri }
    description = cgi["description"].or2 { title }
    cookie = cgi["cookie"].or2 { nil }
    regexp = cgi["regexp"].or2 { nil }
    regexp = Regexp.new(regexp) if regexp
    # 
    options = if cookie then { "Cookie" => cookie } else {} end
    page = open_uri_safe(uri, options) { |io| io.read }
    tracked_content =
      if regexp then
        page = page[regexp].or2 { nil }
      else
        page
      end
    tracked_content_checksum =
      Digest::SHA256.hexdigest(uri + "\n" + tracked_content)
    cgi.out("application/rss+xml") do
      <<-RSS
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
<channel>
  <title>#{CGI.escapeHTML title}</title>
  <link>#{CGI.escapeHTML uri}</link>
  <description>#{CGI.escapeHTML description}</description>
  #{if ttl then "<ttl>#{CGI.escapeHTML ttl}</ttl>" else "" end}
  <item>#{
    if tracked_content then
      <<-RSS
        <title>#{CGI.escapeHTML title}</title>
        <description>The page has been updated</description>
        <link>#{CGI.escapeHTML uri}</link>
        <guid isPermaLink="false">#{tracked_content_checksum}</guid>
      RSS
    else
      <<-RSS
        <title>Error!</title>
        <description>Can not find the content to track! That may be due to an invalid regular expression you specified when creating this RSS feed.</description>
        <link>#{CGI.escapeHTML uri}</link>
        <guid isPermaLink="false">#{CGI.escapeHTML Time.now.to_s}</guid>
      RSS
    end
  }</item>
  </channel>
</rss>
      RSS
    end
  elsif uri.nil?
    cgi.out('text/html; charset="UTF-8"') do
      <<-HTML
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
  <title>Page to RSS</title>
  <style>
    table {
      padding-left: 1em;
    }
    td {
      padding-top: 0.5em;
    }
    td.label {
      text-align: right;
      padding-right: 0.5em;
    }
    td.footnote {
      font-size: 80%;
      text-align: right;
    }
    td.submit {
      padding-top: 1em;
      text-align: right;
    }
  </style>
</head>
<body>
  <p></p>
  Make RSS from any web page.
  <p></p>
  <form action="#{cgi.script_name}" method="GET">
    <table>
      <tr><td class="label">URI:</td><td><input name="uri" required="true"></input>*</td></tr>
      <tr><td class="label">Title:</td><td><input name="title" title="The RSS channel title"></input></td></tr>
      <tr><td class="label">Description:</td><td><input name="description" title="The RSS channel description"></input></td></tr>
      <tr><td class="label">Time to refresh:</td><td><input name="ttl" type="number" min="0" step="5" placeholder="#{DEFAULT_TTL}" title="How often the URI is accessed"></input> min.</td></tr>
      <tr><td class="label">Cookies:</td><td><input name="cookie" placeholder="Key=Value" title="Cookies used to access URI"></td></tr>
      <tr><td class="label">Regexp:</td><td><input name="regexp" title="The web page's part to check for updates"></td></tr>
      <tr><td colspan="2" class="footnote">* Mandatory fields</td></tr>
      <tr><td colspan="2" class="submit"><input type="submit" value="Make RSS"></input></td></tr>
    </table>
  </form>
</body>
</html>
      HTML
    end
  end
rescue Exception => e
  cgi.out("type" => "text/plain", "status" => "400") { e.message }
end
