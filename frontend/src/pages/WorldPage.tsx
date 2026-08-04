import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Map, Search, Globe, ChevronDown, ChevronUp } from 'lucide-react';

interface Country {
  code: string;
  name: string;
  continent: string;
  emoji: string;
  capital: string;
  currency: string;
  cities: string[];
}

export function WorldPage() {
  const [countries, setCountries] = useState<Country[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedContinent, setSelectedContinent] = useState('All');
  const [expandedCountry, setExpandedCountry] = useState<string | null>(null);
  
  const navigate = useNavigate();

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/world/countries')
      .then(res => res.json())
      .then(data => {
        setCountries(data.countries || []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch world data:", err);
        setLoading(false);
      });
  }, []);

  const continents = ['All', 'Europe', 'Asia', 'Americas', 'Africa', 'Oceania'];

  const filteredCountries = countries.filter(c => {
    const matchesContinent = selectedContinent === 'All' || c.continent === selectedContinent;
    const searchLower = search.toLowerCase();
    const matchesSearch = c.name.toLowerCase().includes(searchLower) || 
                          c.cities.some(city => city.toLowerCase().includes(searchLower));
    return matchesContinent && matchesSearch;
  });

  const handleCitySelect = (city: string) => {
    navigate(`/?destination=${encodeURIComponent(city)}`);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      
      <div className="mb-10 text-center">
        <div className="inline-flex items-center justify-center p-3 bg-sage-50 text-sage-600 rounded-2xl mb-4 shadow-sm border border-sage-100">
          <Globe className="w-8 h-8" />
        </div>
        <h1 className="text-4xl font-light text-sage-900 tracking-tight mb-3 font-serif">Dünya Gezgini</h1>
        <p className="text-sage-600 text-lg max-w-2xl mx-auto leading-relaxed">
          Explore the whole world. Explore countries, choose your favorite city, and instantly create your dream travel plan with AI.
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-4 mb-10 items-center justify-between bg-white p-4 rounded-2xl shadow-sm border border-sage-100">
        <div className="flex flex-wrap gap-2 w-full md:w-auto">
          {continents.map(c => (
            <button
              key={c}
              onClick={() => setSelectedContinent(c)}
              className={`px-4 py-2 rounded-full text-sm transition-all duration-300 font-medium ${
                selectedContinent === c
                  ? 'bg-sage-600 text-white shadow-md'
                  : 'bg-sage-50 text-sage-600 hover:bg-sage-100'
              }`}
            >
              {c === 'All' ? 'Tümü' : c}
            </button>
          ))}
        </div>
        
        <div className="relative w-full md:w-72">
          <input
            type="text"
            placeholder="Ülke veya şehir ara..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-sage-50/50 border border-sage-200 rounded-xl focus:ring-2 focus:ring-sage-500 focus:border-transparent transition-all outline-none text-sage-800 placeholder-sage-400 font-medium"
          />
          <Search className="w-5 h-5 text-sage-400 absolute left-3 top-3.5" />
        </div>
      </div>

      {loading && (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sage-600"></div>
        </div>
      )}

      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCountries.map(country => (
            <div 
              key={country.code}
              className={`bg-white rounded-2xl border transition-all duration-300 overflow-hidden ${
                expandedCountry === country.code 
                  ? 'border-sage-300 shadow-md ring-1 ring-sage-100' 
                  : 'border-sage-100 shadow-sm hover:shadow-md hover:border-sage-200'
              }`}
            >
              <div 
                className="p-5 cursor-pointer flex items-center justify-between group"
                onClick={() => setExpandedCountry(expandedCountry === country.code ? null : country.code)}
              >
                <div className="flex items-center gap-4">
                  <div className="text-4xl bg-sage-50 w-14 h-14 rounded-2xl flex items-center justify-center shadow-inner">
                    {country.emoji}
                  </div>
                  <div>
                    <h3 className="text-xl font-medium text-sage-900 group-hover:text-sage-700 transition-colors">
                      {country.name}
                    </h3>
                    <p className="text-sage-500 text-sm mt-0.5">
                      {country.cities.length} Şehir &bull; {country.continent}
                    </p>
                  </div>
                </div>
                <div className="text-sage-400 group-hover:text-sage-600 transition-colors">
                  {expandedCountry === country.code ? <ChevronUp className="w-6 h-6" /> : <ChevronDown className="w-6 h-6" />}
                </div>
              </div>

              {expandedCountry === country.code && (
                <div className="border-t border-sage-100 bg-sage-50/30 p-5">
                  <div className="flex items-center gap-2 mb-4 text-xs font-medium text-sage-500 uppercase tracking-wider">
                    <Map className="w-4 h-4" />
                    <span>Öne Çıkan Şehirler</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {country.cities.map(city => (
                      <button
                        key={city}
                        onClick={(e) => { e.stopPropagation(); handleCitySelect(city); }}
                        className="px-4 py-2 bg-white border border-sage-200 rounded-xl text-sage-700 text-sm hover:border-sage-400 hover:shadow-sm hover:text-sage-900 transition-all font-medium flex items-center gap-2"
                      >
                        {city}
                        {city === country.capital && <span className="text-[10px] bg-sage-100 text-sage-600 px-1.5 py-0.5 rounded-full ml-1">Başkent</span>}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
          
          {filteredCountries.length === 0 && (
            <div className="col-span-full py-20 text-center bg-white rounded-2xl border border-sage-100">
              <Globe className="w-12 h-12 text-sage-300 mx-auto mb-4" />
              <p className="text-sage-600 text-lg">Aramanızla eşleşen bir yer bulunamadı.</p>
              <button 
                onClick={() => {setSearch(''); setSelectedContinent('All');}}
                className="mt-4 text-sage-600 hover:text-sage-800 underline font-medium"
              >
                Aramayı Temizle
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
