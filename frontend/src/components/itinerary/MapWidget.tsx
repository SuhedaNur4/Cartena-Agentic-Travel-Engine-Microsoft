import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

interface MapWidgetProps {
  destination: string
  markers?: { label: string, lat: number, lon: number }[]
}

export function MapWidget({ destination, markers = [] }: MapWidgetProps) {
  const [coords, setCoords] = useState<[number, number] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    const fetchCoords = async () => {
      try {
        const query = encodeURIComponent(destination)
        const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}&limit=1`)
        if (!res.ok) throw new Error('Network response was not ok')
        
        const data = await res.json()
        if (active) {
          if (data && data.length > 0) {
            setCoords([parseFloat(data[0].lat), parseFloat(data[0].lon)])
          } else {
            setError('Konum bulunamadı.')
          }
        }
      } catch (err) {
        if (active) {
          setError('Error loading map.')
        }
      }
    }

    fetchCoords()

    return () => {
      active = false
    }
  }, [destination])

  if (error) {
    return (
      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#F5ECD2', color: '#8c7e6c', fontFamily: '"DM Sans", sans-serif', fontSize: '15px' }}>
        {error}
      </div>
    )
  }

  if (!coords) {
    return (
      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#F5ECD2', color: '#8c7e6c', fontFamily: '"DM Sans", sans-serif', fontSize: '15px' }}>
        Loading map...
      </div>
    )
  }

  return (
    <MapContainer 
      center={coords} 
      zoom={12} 
      scrollWheelZoom={false} 
      style={{ width: '100%', height: '100%', borderRadius: '12px', zIndex: 1 }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Marker position={coords}>
        <Popup>
          <span style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600 }}>{destination} (Merkez)</span>
        </Popup>
      </Marker>
      {markers.map((m, i) => (
        <Marker key={i} position={[m.lat, m.lon]}>
          <Popup>
            <span style={{ fontFamily: '"DM Sans", sans-serif', fontWeight: 600 }}>{m.label}</span>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
