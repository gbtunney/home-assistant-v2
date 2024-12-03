# Homeassistant Config Notes

## Camera Media Save Source
- the mapping is :      VIDEO PATH : camera_media/videos
- Camera Media Image Mappings:
    - VIDEO: 
      - path: (camera_media/?)/videos
      - extention: "mp4" (todo: change from ffmpeg?)
      - content_mime_type: "video/mp4"

    - IMAGES:
      - path: (camera_media/?)/images
      - extention: "jpeg" or png? (todo: change from ffmpeg?)
      - content_mime_type: "image/png" (png)
      - content_mime_type: "image/jpeg" (jpeg)

FIlE FORMAT - 
{{ directory }}/{{prefix }}-{{ as_timestamp(now()) }}.{{ext}}

{{ directory = ( videos | images ) }} / {{ entity_id }} - {{ as_timestamp(now()) }}. 


```yaml

# directory ==  
{% set mime_type = "video/mp4" %}  # Replace this with your actual MIME type variable
{% set type = mime_type.split('/')[0] %}
{%  if  type in ['video', 'image'] %}{{ type }}{% else %}video{% endif %}


ext:

    {% set mime_type = "video/mp4" %}  # Replace this with your actual MIME type variable
    {% if mime_type | regex_match('^(video|image)/[a-z]{3,4}$') %}
      {% else &}
     {% set mime_type = "video/mp4" %}
    {% endif %}


    #file_ext
  {% set mime_ext = mime_type.split('/')[1] %}
  {% if mime_ext | length => 3 %}{% set file_ext = mime_ext | default('jpeg') %}{% endif %}
    # mime_domain
  {% set mime_domain = mime_type.split('/')[0] %}

# should bbe entityid 
  {% macro camera_media_path( entity_id = 'camera-entity-unknown', mime_type = "video/mp4" ) %}
     
      {% if mime_type | regex_match('^(video|image)/[a-z]{3,4}$') %}
      {% else &}
      {% set mime_type = "video/mp4" %}
      {% endif %}
      # validate and set mimetype

      #file_ext
      {% set mime_ext = mime_type.split('/')[1] %}
      {% if mime_ext | length => 3 %}{% set file_ext = mime_ext | default('jpeg') %}{% endif %}
      # mime_domain
      {% set mime_domain = mime_type.split('/')[0] %}
      {{ mime_domain }}/{{ entity_id }}-{{ as_timestamp(now()) }}.{{ file_ext }}
  {% endmacro %}
  
  
  {% set media_lib_directory = "/media" %}
      
  {{ directory }}/{{prefix }}-{{ as_timestamp(now()) }}.{{ext}}
 
      
      
      {{ mime_domain }}/{{ prefix }}-{{ as_timestamp(now()) }}.{{ file_ext }}
    
    
                                                     // {%  if  type in ['video', 'image'] %}{{ type }}{% else %}video{% endif %}
^(video|image)\/[a-z]{3,4}$

{{ type }}/{{ entity_id }}-{{ as_timestamp(now()) }}.{{ mime_type.split('/')[1] }}

  {% set mime_type = "video/mp4" %}  # Replace this with your actual MIME type variable
  {% if mime_type | regex_match('^(video|image)/[a-z]{3,4}$') %}
  {{ mime_type }}{% else %}{{ 'video/mp4'  }}{% endif %}

```
