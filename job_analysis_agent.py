# Système d'Agent IA pour l'Analyse du Marché de l'Emploi
# =====================================================
# Un système multi-agents capable de scraper LinkedIn et Indeed,
# analyser les données d'emploi et identifier les tendances importantes.

import asyncio
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pandas as pd
import json
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class JobPosting:
    """Structure de données pour une offre d'emploi"""
    title: str
    company: str
    location: str
    description: str
    technologies: List[str]
    frameworks: List[str]
    certifications: List[str]
    salary_range: str
    date_posted: str
    recruiter: str
    url: str


class JobScraper:
    """Classe de base pour le scraping d'emplois"""

    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.driver = None

    def setup_driver(self):
        """Initialise le driver Selenium"""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du driver: {e}")
            return False

    def close_driver(self):
        """Ferme le driver Selenium"""
        if self.driver:
            self.driver.quit()


class LinkedInScraper(JobScraper):
    """Scraper spécialisé pour LinkedIn"""

    def __init__(self, keywords: List[str]):
        super().__init__()
        self.keywords = keywords
        self.base_url = "https://www.linkedin.com/jobs/search"

    async def scrape_jobs(self, location: str = "", limit: int = 100) -> List[JobPosting]:
        """Scrape les emplois sur LinkedIn"""
        jobs = []

        if not self.setup_driver():
            return jobs

        try:
            for keyword in self.keywords:
                url = f"{self.base_url}?keywords={keyword}&location={location}"
                self.driver.get(url)

                # Attendre le chargement de la page
                await asyncio.sleep(5)

                # Parser les offres d'emploi
                jobs_elements = self.driver.find_elements("css selector", ".job-search-card")

                for job_element in jobs_elements[:limit]:
                    try:
                        job = self._parse_linkedin_job(job_element)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.error(f"Erreur lors du parsing d'un emploi: {e}")
                        continue

        except Exception as e:
            logger.error(f"Erreur lors du scraping LinkedIn: {e}")
        finally:
            self.close_driver()

        return jobs

    def _parse_linkedin_job(self, job_element) -> JobPosting:
        """Parse un élément d'emploi LinkedIn"""
        try:
            title = job_element.find_element("css selector", "h3").text
            company = job_element.find_element("css selector",
                                               "a[data-tracking-control-name='public_jobs_jserp-result_job-search-card-subtitle']").text
            location = job_element.find_element("css selector", ".job-search-card__location").text
            url = job_element.find_element("css selector", "a").get_attribute("href")

            # Extraire plus de détails en cliquant sur l'offre
            job_details = self._get_job_details(url)

            return JobPosting(
                title=title,
                company=company,
                location=location,
                description=job_details.get('description', ''),
                technologies=job_details.get('technologies', []),
                frameworks=job_details.get('frameworks', []),
                certifications=job_details.get('certifications', []),
                salary_range=job_details.get('salary', ''),
                date_posted=job_details.get('date', ''),
                recruiter=job_details.get('recruiter', ''),
                url=url
            )
        except Exception as e:
            logger.error(f"Erreur lors du parsing: {e}")
            return None

    def _get_job_details(self, url: str) -> Dict[str, Any]:
        """Récupère les détails d'une offre d'emploi"""
        try:
            self.driver.get(url)
            asyncio.sleep(2)

            description_element = self.driver.find_element("css selector", ".show-more-less-html__markup")
            description = description_element.text if description_element else ""

            # Analyse IA de la description pour extraire technologies, frameworks, etc.
            analysis = self._analyze_job_description(description)

            return {
                'description': description,
                'technologies': analysis.get('technologies', []),
                'frameworks': analysis.get('frameworks', []),
                'certifications': analysis.get('certifications', []),
                'salary': analysis.get('salary', ''),
                'date': datetime.now().strftime("%Y-%m-%d"),
                'recruiter': analysis.get('recruiter', '')
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des détails: {e}")
            return {}

    def _analyze_job_description(self, description: str) -> Dict[str, List[str]]:
        """Analyse la description d'emploi avec IA pour extraire les informations"""
        # Liste des technologies populaires à rechercher
        tech_keywords = [
            'Python', 'Java', 'JavaScript', 'C++', 'C#', 'Go', 'Rust', 'Swift',
            'TypeScript', 'Kotlin', 'PHP', 'Ruby', 'Scala', 'R', 'SQL'
        ]

        framework_keywords = [
            'React', 'Angular', 'Vue.js', 'Django', 'Flask', 'Spring', 'Express',
            'Laravel', 'Rails', 'ASP.NET', 'Symfony', 'Bootstrap', 'jQuery'
        ]

        cert_keywords = [
            'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'CISSP', 'CISM',
            'PMP', 'Scrum', 'Agile', 'DevOps', 'ITIL', 'CompTIA', 'Cisco'
        ]

        found_tech = [tech for tech in tech_keywords if tech.lower() in description.lower()]
        found_frameworks = [fw for fw in framework_keywords if fw.lower() in description.lower()]
        found_certs = [cert for cert in cert_keywords if cert.lower() in description.lower()]

        return {
            'technologies': found_tech,
            'frameworks': found_frameworks,
            'certifications': found_certs,
            'salary': self._extract_salary(description),
            'recruiter': self._extract_recruiter_info(description)
        }

    def _extract_salary(self, description: str) -> str:
        """Extrait les informations de salaire de la description"""
        import re
        salary_patterns = [
            r'\$[\d,]+\s*-\s*\$[\d,]+',
            r'\$[\d,]+k?\s*-\s*\$[\d,]+k?',
            r'[\d,]+\s*-\s*[\d,]+\s*€',
            r'[\d,]+k?\s*-\s*[\d,]+k?\s*€'
        ]

        for pattern in salary_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group()

        return ""

    def _extract_recruiter_info(self, description: str) -> str:
        """Extrait les informations sur le recruteur"""
        # Logique pour identifier les informations de contact du recruteur
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, description)

        if email_match:
            return email_match.group()

        return ""


class IndeedScraper(JobScraper):
    """Scraper spécialisé pour Indeed"""

    def __init__(self, keywords: List[str]):
        super().__init__()
        self.keywords = keywords
        self.base_url = "https://www.indeed.com/jobs"

    async def scrape_jobs(self, location: str = "", limit: int = 100) -> List[JobPosting]:
        """Scrape les emplois sur Indeed"""
        jobs = []

        if not self.setup_driver():
            return jobs

        try:
            for keyword in self.keywords:
                url = f"{self.base_url}?q={keyword}&l={location}"
                self.driver.get(url)

                await asyncio.sleep(3)

                # Parser les offres d'emploi Indeed
                jobs_elements = self.driver.find_elements("css selector", ".jobsearch-SerpJobCard")

                for job_element in jobs_elements[:limit]:
                    try:
                        job = self._parse_indeed_job(job_element)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.error(f"Erreur lors du parsing d'un emploi Indeed: {e}")
                        continue

        except Exception as e:
            logger.error(f"Erreur lors du scraping Indeed: {e}")
        finally:
            self.close_driver()

        return jobs

    def _parse_indeed_job(self, job_element) -> JobPosting:
        """Parse un élément d'emploi Indeed"""
        # Implémentation similaire à LinkedIn mais adaptée à la structure Indeed
        try:
            title_element = job_element.find_element("css selector", "h2 a span")
            title = title_element.get_attribute("title") if title_element else ""

            company_element = job_element.find_element("css selector", ".companyName")
            company = company_element.text if company_element else ""

            location_element = job_element.find_element("css selector", ".companyLocation")
            location = location_element.text if location_element else ""

            url_element = job_element.find_element("css selector", "h2 a")
            relative_url = url_element.get_attribute("href") if url_element else ""
            url = f"https://www.indeed.com{relative_url}" if relative_url else ""

            # Récupérer les détails de l'emploi
            job_details = self._get_indeed_job_details(url)

            return JobPosting(
                title=title,
                company=company,
                location=location,
                description=job_details.get('description', ''),
                technologies=job_details.get('technologies', []),
                frameworks=job_details.get('frameworks', []),
                certifications=job_details.get('certifications', []),
                salary_range=job_details.get('salary', ''),
                date_posted=job_details.get('date', ''),
                recruiter=job_details.get('recruiter', ''),
                url=url
            )
        except Exception as e:
            logger.error(f"Erreur lors du parsing Indeed: {e}")
            return None

    def _get_indeed_job_details(self, url: str) -> Dict[str, Any]:
        """Récupère les détails d'une offre Indeed"""
        # Implémentation similaire mais adaptée à Indeed
        return self._analyze_job_description("")  # Simplification


class JobMarketAnalyzer:
    """Analyseur de marché de l'emploi avec IA"""

    def __init__(self):
        self.jobs_data = []

    def analyze_trends(self, jobs: List[JobPosting]) -> Dict[str, Any]:
        """Analyse les tendances du marché de l'emploi"""
        analysis = {
            'total_jobs': len(jobs),
            'top_technologies': self._get_top_items([tech for job in jobs for tech in job.technologies]),
            'top_frameworks': self._get_top_items([fw for job in jobs for fw in job.frameworks]),
            'top_certifications': self._get_top_items([cert for job in jobs for cert in job.certifications]),
            'top_companies': self._get_top_items([job.company for job in jobs]),
            'top_locations': self._get_top_items([job.location for job in jobs]),
            'salary_analysis': self._analyze_salaries(jobs),
            'recruiter_insights': self._analyze_recruiters(jobs)
        }

        return analysis

    def _get_top_items(self, items: List[str], top_n: int = 10) -> Dict[str, int]:
        """Retourne les top N éléments les plus fréquents"""
        from collections import Counter
        counter = Counter(items)
        return dict(counter.most_common(top_n))

    def _analyze_salaries(self, jobs: List[JobPosting]) -> Dict[str, Any]:
        """Analyse les salaires"""
        salaries = [job.salary_range for job in jobs if job.salary_range]
        return {
            'total_with_salary': len(salaries),
            'percentage_with_salary': len(salaries) / len(jobs) * 100 if jobs else 0,
            'salary_ranges': self._get_top_items(salaries)
        }

    def _analyze_recruiters(self, jobs: List[JobPosting]) -> Dict[str, Any]:
        """Analyse les informations sur les recruteurs"""
        recruiters = [job.recruiter for job in jobs if job.recruiter]
        return {
            'total_with_recruiter_info': len(recruiters),
            'percentage_with_recruiter_info': len(recruiters) / len(jobs) * 100 if jobs else 0,
            'top_recruiters': self._get_top_items(recruiters)
        }


class AIJobAgent:
    """Agent principal coordonnant toutes les activités"""

    def __init__(self, openai_api_key: str = None):
        self.linkedin_scraper = None
        self.indeed_scraper = None
        self.analyzer = JobMarketAnalyzer()
        self.openai_api_key = openai_api_key

        # Configuration des mots-clés de recherche
        self.default_keywords = [
            "Python Developer", "Java Developer", "JavaScript Developer",
            "Data Scientist", "Machine Learning Engineer", "DevOps Engineer",
            "Full Stack Developer", "Backend Developer", "Frontend Developer",
            "AI Engineer", "Cloud Engineer", "Cybersecurity Analyst", "Deep Learning"
        ]

    async def run_full_analysis(self,
                                keywords: List[str] = None,
                                locations: List[str] = ["Paris", "Lyon", "Marseille"],
                                limit_per_site: int = 50) -> Dict[str, Any]:
        """Lance une analyse complète du marché de l'emploi"""

        keywords = keywords or self.default_keywords

        logger.info("Démarrage de l'analyse complète du marché de l'emploi...")

        # Initialisation des scrapers
        self.linkedin_scraper = LinkedInScraper(keywords)
        self.indeed_scraper = IndeedScraper(keywords)

        all_jobs = []

        # Scraping LinkedIn
        logger.info("Scraping LinkedIn...")
        for location in locations:
            linkedin_jobs = await self.linkedin_scraper.scrape_jobs(location, limit_per_site)
            all_jobs.extend(linkedin_jobs)
            logger.info(f"LinkedIn {location}: {len(linkedin_jobs)} emplois collectés")

        # Scraping Indeed
        logger.info("Scraping Indeed...")
        for location in locations:
            indeed_jobs = await self.indeed_scraper.scrape_jobs(location, limit_per_site)
            all_jobs.extend(indeed_jobs)
            logger.info(f"Indeed {location}: {len(indeed_jobs)} emplois collectés")

        # Analyse des données
        logger.info("Analyse des données collectées...")
        analysis = self.analyzer.analyze_trends(all_jobs)

        # Génération de recommandations IA
        recommendations = await self._generate_ai_recommendations(analysis)

        # Compilation des résultats finaux
        final_report = {
            'metadata': {
                'total_jobs_collected': len(all_jobs),
                'keywords_used': keywords,
                'locations_searched': locations,
                'analysis_date': datetime.now().isoformat()
            },
            'market_analysis': analysis,
            'ai_recommendations': recommendations,
            'raw_jobs_data': [vars(job) for job in all_jobs]  # Conversion en dict pour sérialisation
        }

        # Sauvegarde des résultats
        self._save_results(final_report)

        logger.info("Analyse complète terminée!")
        return final_report

    async def _generate_ai_recommendations(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Génère des recommandations basées sur l'analyse IA"""

        recommendations = {
            'top_skills_to_learn': [],
            'emerging_technologies': [],
            'certification_priorities': [],
            'market_opportunities': [],
            'recruiter_networking_tips': []
        }

        # Analyse des technologies les plus demandées
        top_tech = analysis.get('top_technologies', {})
        if top_tech:
            sorted_tech = sorted(top_tech.items(), key=lambda x: x[1], reverse=True)
            recommendations['top_skills_to_learn'] = [
                {
                    'technology': tech,
                    'job_count': count,
                    'priority': 'High' if count > 10 else 'Medium' if count > 5 else 'Low'
                }
                for tech, count in sorted_tech[:10]
            ]

        # Analyse des frameworks
        top_frameworks = analysis.get('top_frameworks', {})
        if top_frameworks:
            recommendations['emerging_technologies'] = [
                {
                    'framework': fw,
                    'usage_frequency': count,
                    'learning_recommendation': self._get_learning_recommendation(fw)
                }
                for fw, count in sorted(top_frameworks.items(), key=lambda x: x[1], reverse=True)[:5]
            ]

        # Analyse des certifications
        top_certs = analysis.get('top_certifications', {})
        if top_certs:
            recommendations['certification_priorities'] = [
                {
                    'certification': cert,
                    'demand_level': count,
                    'estimated_roi': self._estimate_certification_roi(cert)
                }
                for cert, count in sorted(top_certs.items(), key=lambda x: x[1], reverse=True)[:5]
            ]

        # Opportunités de marché
        top_locations = analysis.get('top_locations', {})
        if top_locations:
            recommendations['market_opportunities'] = [
                {
                    'location': location,
                    'job_availability': count,
                    'market_attractiveness': 'High' if count > 20 else 'Medium' if count > 10 else 'Low'
                }
                for location, count in sorted(top_locations.items(), key=lambda x: x[1], reverse=True)[:5]
            ]

        # Conseils pour le networking avec les recruteurs
        recommendations['recruiter_networking_tips'] = [
            "Optimisez votre profil LinkedIn avec les technologies les plus demandées",
            "Participez à des événements tech dans les villes avec le plus d'opportunités",
            "Obtenez des certifications dans les domaines les plus recherchés",
            "Développez des projets portfolio utilisant les frameworks populaires",
            "Rejoignez des communautés professionnelles liées aux technologies émergentes"
        ]

        return recommendations

    def _get_learning_recommendation(self, framework: str) -> str:
        """Retourne une recommandation d'apprentissage pour un framework"""
        recommendations = {
            'React': 'Plateforme recommandée: React Official Docs + freeCodeCamp',
            'Angular': 'Plateforme recommandée: Angular University + Pluralsight',
            'Vue.js': 'Plateforme recommandée: Vue Mastery + Udemy',
            'Django': 'Plateforme recommandée: Django Official Tutorial + Real Python',
            'Flask': 'Plateforme recommandée: Flask Mega-Tutorial + YouTube',
            'Spring': 'Plateforme recommandée: Spring.io Guides + Baeldung'
        }
        return recommendations.get(framework, 'Plateforme recommandée: Documentation officielle + Udemy/Coursera')

    def _estimate_certification_roi(self, certification: str) -> str:
        """Estime le ROI d'une certification"""
        high_roi_certs = ['AWS', 'Azure', 'GCP', 'CISSP', 'CISM', 'PMP']
        medium_roi_certs = ['Docker', 'Kubernetes', 'Scrum', 'DevOps']

        if any(cert in certification for cert in high_roi_certs):
            return 'High ROI (15-30% salary increase potential)'
        elif any(cert in certification for cert in medium_roi_certs):
            return 'Medium ROI (10-20% salary increase potential)'
        else:
            return 'Variable ROI (5-15% salary increase potential)'

    def _save_results(self, report: Dict[str, Any]):
        """Sauvegarde les résultats de l'analyse"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Sauvegarde JSON
        with open(f'job_market_analysis_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # Sauvegarde CSV des emplois
        if report.get('raw_jobs_data'):
            df = pd.DataFrame(report['raw_jobs_data'])
            df.to_csv(f'jobs_data_{timestamp}.csv', index=False, encoding='utf-8')

        logger.info(f"Résultats sauvegardés: job_market_analysis_{timestamp}.json et jobs_data_{timestamp}.csv")


# Fonction principale d'utilisation
async def main():
    """Fonction principale pour lancer l'analyse"""

    # Configuration
    OPENAI_API_KEY = "your-openai-api-key-here"  # Remplacer par votre clé API

    # Initialisation de l'agent
    agent = AIJobAgent(OPENAI_API_KEY)

    # Mots-clés personnalisés (optionnel)
    custom_keywords = [
        "Python Developer",
        "Data Scientist",
        "Machine Learning Engineer",
        "DevOps Engineer",
        "Full Stack Developer"
    ]

    # Lancement de l'analyse complète
    try:
        results = await agent.run_full_analysis(
            keywords=custom_keywords,
            locations=["Paris", "Lyon", "Toulouse", "Nantes"],
            limit_per_site=30
        )

        print("\n" + "=" * 50)
        print("ANALYSE COMPLETE DU MARCHE DE L'EMPLOI")
        print("=" * 50)
        print(f"Total d'emplois analysés: {results['metadata']['total_jobs_collected']}")
        print(f"Date d'analyse: {results['metadata']['analysis_date']}")

        print("\n--- TOP 5 TECHNOLOGIES LES PLUS DEMANDEES ---")
        for skill in results['ai_recommendations']['top_skills_to_learn'][:5]:
            print(f"• {skill['technology']}: {skill['job_count']} emplois ({skill['priority']} priorité)")

        print("\n--- TOP 5 CERTIFICATIONS RECOMMANDEES ---")
        for cert in results['ai_recommendations']['certification_priorities'][:5]:
            print(f"• {cert['certification']}: {cert['demand_level']} demandes ({cert['estimated_roi']})")

        print("\n--- OPPORTUNITES DE MARCHE ---")
        for opportunity in results['ai_recommendations']['market_opportunities'][:3]:
            print(
                f"• {opportunity['location']}: {opportunity['job_availability']} emplois ({opportunity['market_attractiveness']} attractivité)")

        print("\nRésultats complets sauvegardés dans les fichiers JSON et CSV.")

    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {e}")
        print(f"Erreur: {e}")


# Script d'exécution
if __name__ == "__main__":
    print("\n\nSystème d'Agent IA pour l'Analyse du Marché de l'Emploi")
    print("=" * 55)
    print("\nDémarrage de l'analyse...")

    # Pour exécuter le script:
    asyncio.run(main())

    print("\nCode généré avec succès!")
    print("\nPour utiliser ce système:")
    print("1. Installez les dépendances requises")
    print("2. Configurez votre clé API OpenAI")
    print("3. Exécutez: python job_analysis_agent.py")