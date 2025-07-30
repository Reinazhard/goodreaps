import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from textblob import TextBlob
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import seaborn as sns
from collections import Counter
import warnings
import io
import base64
import logging

# Suppress warnings
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)


# Download required NLTK data
@st.cache_resource
def download_nltk_data():
    try:
        nltk.data.find("tokenizers/punkt")
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("punkt")
        nltk.download("stopwords")


class ReviewPreprocessor:
    """Handle text preprocessing for reviews"""

    def __init__(self):
        self.stop_words = set(stopwords.words("english"))
        self.stemmer = PorterStemmer()

    def clean_text(self, text):
        """Clean and preprocess text"""
        if pd.isna(text) or text == "":
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", str(text))

        # Remove URLs
        text = re.sub(r"http\S+|www.\S+", "", text)

        # Remove special characters and digits
        text = re.sub(r"[^a-zA-Z\s]", "", text)

        # Convert to lowercase
        text = text.lower()

        # Tokenize
        tokens = word_tokenize(text)

        # Remove stopwords and short words
        tokens = [
            token for token in tokens if token not in self.stop_words and len(token) > 2
        ]

        # Stem words
        tokens = [self.stemmer.stem(token) for token in tokens]

        return " ".join(tokens)

    def is_valid_review(self, text, min_length=10):
        """Check if review is valid for analysis"""
        if pd.isna(text) or text == "":
            return False
        return len(str(text).split()) >= min_length


class SentimentAnalyzer:
    """Handle sentiment analysis using transformer models"""

    def __init__(self, confidence_threshold=0.6, chunk_size=400):
        self.confidence_threshold = confidence_threshold
        self.chunk_size = chunk_size
        pipeline_result = self._load_transformer_model()

        if pipeline_result[0] is not None:
            self.transformer_model, self.tokenizer, self.model = pipeline_result
        else:
            st.error("Failed to load transformer model")
            self.transformer_model = None
            self.tokenizer = None
            self.model = None

    @st.cache_resource
    def _load_transformer_model(_self):
        """Load pretrained transformer model with explicit tokenizer and model"""
        try:
            # Load tokenizer and model explicitly for better control
            tokenizer = AutoTokenizer.from_pretrained(
                "nlptown/bert-base-multilingual-uncased-sentiment",
                #use_fast=True,  # Use fast tokenizer for better performance
                model_max_length=512,
            )

            model = AutoModelForSequenceClassification.from_pretrained(
                "nlptown/bert-base-multilingual-uncased-sentiment",
                num_labels=5,  # 1-5 star ratings
                return_dict=True,
            )

            # Create pipeline with explicit components
            sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=model,
                tokenizer=tokenizer,
                device=-1,  # Use CPU
                max_length=512,
                truncation=True,
                padding=True,
                return_all_scores=True,  # Get confidence for all labels
            )

            return sentiment_pipeline, tokenizer, model

        except Exception as e:
            st.error(f"Error loading model: {str(e)}")
            return None, None, None

    def _chunk_text(self, text, max_length=None):
        """Split long text into chunks for better analysis"""
        if max_length is None:
            max_length = self.chunk_size

        words = text.split()
        if len(words) <= max_length:
            return [text]

        chunks = []
        for i in range(0, len(words), max_length):
            chunk = " ".join(words[i : i + max_length])
            chunks.append(chunk)
        return chunks

    def analyze_sentiment_transformer(self, text):
        """Analyze sentiment using transformer model with explicit tokenizer control"""
        if not text or text.strip() == "" or self.transformer_model is None:
            return "neutral", 0.0

        try:
            # For long texts, split into chunks and analyze each
            chunks = self._chunk_text(text)

            chunk_results = []
            for chunk in chunks:
                # Check token count before processing
                tokens = self.tokenizer.encode(chunk, truncation=True, max_length=512)
                if len(tokens) > 510:  # Leave room for special tokens
                    # Truncate if still too long
                    chunk = self.tokenizer.decode(
                        tokens[:510], skip_special_tokens=True
                    )

                result = self.transformer_model(chunk)[0]

                # Find the highest confidence prediction
                max_result = max(result, key=lambda x: x["score"])
                label = max_result["label"]
                confidence = max_result["score"]

                # Map star rating to sentiment
                if "1 star" in label or "2 stars" in label:
                    sentiment = "negative"
                elif "4 stars" in label or "5 stars" in label:
                    sentiment = "positive"
                else:
                    sentiment = "neutral"

                # Apply confidence threshold
                if confidence < self.confidence_threshold:
                    sentiment = "neutral"

                chunk_results.append(
                    {
                        "sentiment": sentiment,
                        "confidence": confidence,
                        "original_label": label,
                    }
                )

            # Aggregate results from all chunks
            if len(chunk_results) == 1:
                return chunk_results[0]["sentiment"], chunk_results[0]["confidence"]

            # For multiple chunks, use weighted average based on confidence
            sentiments = [r["sentiment"] for r in chunk_results]
            confidences = [r["confidence"] for r in chunk_results]

            # Calculate weighted sentiment scores
            pos_score = sum(
                conf
                for sent, conf in zip(sentiments, confidences)
                if sent == "positive"
            )
            neg_score = sum(
                conf
                for sent, conf in zip(sentiments, confidences)
                if sent == "negative"
            )
            neu_score = sum(
                conf for sent, conf in zip(sentiments, confidences) if sent == "neutral"
            )

            max_score = max(pos_score, neg_score, neu_score)
            avg_confidence = np.mean(confidences)

            if max_score == pos_score and pos_score > 0:
                return "positive", avg_confidence
            elif max_score == neg_score and neg_score > 0:
                return "negative", avg_confidence
            else:
                return "neutral", avg_confidence

        except Exception as e:
            st.warning(f"Error in sentiment analysis: {str(e)}")
            return "neutral", 0.0

    def analyze_batch(self, texts):
        """Analyze sentiment for a batch of texts"""
        results = []
        for text in texts:
            sentiment, confidence = self.analyze_sentiment_transformer(text)
            results.append({"sentiment": sentiment, "confidence": confidence})
        return results


class DataGenerator:
    """Generate sample Goodreads-like data for demonstration"""

    @staticmethod
    def generate_sample_data(n_reviews=1000):
        """Generate sample review data"""
        np.random.seed(42)

        # Sample book titles
        books = [
            "The Great Gatsby",
            "To Kill a Mockingbird",
            "1984",
            "Pride and Prejudice",
            "The Catcher in the Rye",
            "Lord of the Flies",
            "Harry Potter and the Sorcerer's Stone",
            "The Hobbit",
            "Fahrenheit 451",
            "Jane Eyre",
            "Wuthering Heights",
            "The Chronicles of Narnia",
        ]

        # Sample positive review templates
        positive_reviews = [
            "This book was absolutely amazing and fantastic! I loved every page and couldn't put it down. Brilliant writing!",
            "What a wonderful masterpiece! The author's writing is beautiful and the story is incredible. Highly recommend this excellent book!",
            "One of the best books ever! The narrative is compelling and the themes are amazing. A fantastic classic!",
            "Brilliant and outstanding storytelling! The book was perfect and kept me engaged. Excellent character development throughout.",
            "Exceptional and marvelous work! The plot was surprising and the ending was satisfying. Amazing author with great talent.",
            "This fantastic book changed my life. Beautiful prose and unforgettable characters. A wonderful must-read experience!",
            "Captivating and amazing from start to finish. The author is talented and gifted. Absolutely loved this incredible story!",
            "A phenomenal and outstanding read! The book is entertaining and brilliant. Perfect characters that feel wonderful and inspiring.",
        ]

        # Sample negative review templates
        negative_reviews = [
            "This book was terrible and disappointing. The plot was boring and the characters were poorly written. Waste of time.",
            "Absolutely hated this book. It was confusing, poorly structured, and not worth reading. Very disappointing experience.",
            "One of the worst books I've ever read. The story made no sense and the writing was awful. Don't bother.",
            "Terrible book with bad characters and a horrible plot. I regret buying this. Complete waste of money.",
            "This was boring, badly written, and frustrating to read. The author clearly doesn't know how to write.",
            "Awful book that I couldn't finish. Poor quality writing and an uninteresting story. Very bad.",
            "Disappointing and poorly executed. The book was confusing and the characters were unlikeable. Not recommended.",
            "This book was terrible from start to finish. Bad writing, poor plot, and annoying characters throughout.",
        ]

        # Sample neutral review templates
        neutral_reviews = [
            "It was an okay read. Not bad but not great either. Some parts were interesting, others not so much.",
            "The book was decent. Had its moments but overall just average. Might appeal to some readers.",
            "Mixed feelings about this one. Good writing but the story didn't resonate with me personally.",
            "Not terrible but not amazing either. It's a solid book if you're into this genre.",
            "The book was fine. Some good points and some weak points. It's worth reading if you have time.",
            "Average book with average characters. Nothing spectacular but not bad either.",
            "It was readable but forgettable. The kind of book you read once and don't think about again.",
        ]

        data = []

        for i in range(n_reviews):
            # Generate rating and corresponding review sentiment
            rating = np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.1, 0.2, 0.35, 0.3])

            if rating >= 4:
                review_text = np.random.choice(positive_reviews)
                # Add some variation
                if np.random.random() > 0.7:
                    review_text += " " + np.random.choice(
                        [
                            "Great job by the author!",
                            "Will read again!",
                            "Five stars!",
                            "Couldn't ask for more!",
                            "Perfect execution!",
                        ]
                    )
            elif rating <= 2:
                review_text = np.random.choice(negative_reviews)
                if np.random.random() > 0.7:
                    review_text += " " + np.random.choice(
                        [
                            "Not recommended.",
                            "Save your money.",
                            "Skip this one.",
                            "Very disappointing.",
                            "Waste of time.",
                        ]
                    )
            else:
                review_text = np.random.choice(neutral_reviews)

            # Generate random date within last 2 years
            start_date = datetime.now() - timedelta(days=730)
            random_date = start_date + timedelta(days=np.random.randint(0, 730))

            # Ensure rating is between 1-5 (float)
            rating = max(1.0, min(5.0, float(rating)))

            data.append(
                {
                    "book_title": np.random.choice(books),
                    "rating": rating,
                    "review_text": review_text,
                    "date": random_date.strftime(
                        "%Y-%m-%d"
                    ),  # Changed from review_date to date
                    "reviewer": f"User_{i + 1:04d}",
                    "helpful_votes": np.random.randint(0, 50),
                }
            )

        return pd.DataFrame(data)


class Dashboard:
    """Main dashboard class"""

    def __init__(self):
        self.preprocessor = ReviewPreprocessor()
        self.sentiment_analyzer = None
        self.df = None
        self.analyzed_df = None  # Store analyzed results

    def setup_page(self):
        """Setup Streamlit page configuration"""
        st.set_page_config(
            page_title="Goodreads Sentiment Analysis",
            page_icon="📚",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        st.title("📚 Goodreads Review Sentiment Analysis Dashboard")
        st.markdown("---")

    def sidebar_controls(self):
        """Create sidebar controls"""
        st.sidebar.header("🎛️ Configuration")

        # Fine-tuning parameters
        st.sidebar.subheader("🔧 Analysis Parameters")

        confidence_threshold = st.sidebar.slider(
            "Confidence Threshold:",
            min_value=0.1,
            max_value=0.9,
            value=0.6,
            step=0.05,
            help="Lower values = more sensitive to sentiment, Higher values = more neutral classifications",
        )

        chunk_size = st.sidebar.slider(
            "Text Chunk Size (words):",
            min_value=200,
            max_value=600,
            value=400,
            step=50,
            help="Size of text chunks for long reviews. Smaller chunks = more detailed analysis",
        )

        # Data source selection
        st.sidebar.subheader("📊 Data Source")
        data_source = st.sidebar.radio(
            "Choose Data Source:", ["Use Sample Data", "Upload CSV File"]
        )

        # Sample data size if using sample data
        sample_size = 1000
        if data_source == "Use Sample Data":
            sample_size = st.sidebar.slider(
                "Number of Sample Reviews:",
                min_value=100,
                max_value=2000,
                value=1000,
                step=100,
            )

        return confidence_threshold, chunk_size, data_source, sample_size

    def load_data(self, data_source, sample_size):
        """Load data based on source selection"""
        if data_source == "Use Sample Data":
            with st.spinner("Generating sample data..."):
                self.df = DataGenerator.generate_sample_data(sample_size)
                st.success(f"Generated {len(self.df)} sample reviews!")
        else:
            uploaded_file = st.sidebar.file_uploader(
                "Upload CSV file",
                type=["csv"],
                help="CSV should contain columns: book_title, rating, review_text, review_date",
            )

            if uploaded_file is not None:
                try:
                    self.df = pd.read_csv(uploaded_file)
                    st.success(f"Loaded {len(self.df)} reviews from file!")
                except Exception as e:
                    st.error(f"Error loading file: {str(e)}")
                    return False
            else:
                st.info("Please upload a CSV file to proceed.")
                return False

        return True

    def preprocess_data(self):
        """Preprocess the loaded data"""
        if self.df is None:
            return

        with st.spinner("Preprocessing data..."):
            # Clean review texts
            self.df["cleaned_text"] = self.df["review_text"].apply(
                self.preprocessor.clean_text
            )

            # Filter valid reviews
            valid_mask = self.df["review_text"].apply(self.preprocessor.is_valid_review)
            self.df = self.df[valid_mask].copy()

            # Convert date column
            if "date" in self.df.columns:
                self.df["date"] = pd.to_datetime(self.df["date"])
            elif "review_date" in self.df.columns:
                self.df["date"] = pd.to_datetime(self.df["review_date"])
                self.df = self.df.drop("review_date", axis=1)

            # Ensure ratings are between 1-5 (float)
            self.df["rating"] = self.df["rating"].astype(float)
            self.df = self.df[(self.df["rating"] >= 1.0) & (self.df["rating"] <= 5.0)]

            # Add review length
            self.df["review_length"] = self.df["review_text"].str.split().str.len()

            # Remove duplicates
            initial_count = len(self.df)
            self.df = self.df.drop_duplicates(subset=["review_text"]).copy()
            removed_count = initial_count - len(self.df)

            if removed_count > 0:
                st.info(f"Removed {removed_count} duplicate reviews.")

    @st.cache_data
    def perform_sentiment_analysis(
        _self, review_texts, confidence_threshold, chunk_size
    ):
        """Perform sentiment analysis on reviews with caching"""

        with st.spinner("Analyzing sentiment using BERT multilingual model..."):
            # Analyze sentiment in batches for better performance
            batch_size = 40  # Smaller batch size for transformer
            results = []

            progress_bar = st.progress(0)
            total_batches = (len(review_texts) + batch_size - 1) // batch_size

            for i in range(0, len(review_texts), batch_size):
                batch = review_texts[i : i + batch_size]
                batch_results = _self.sentiment_analyzer.analyze_batch(batch)
                results.extend(batch_results)

                progress = min((i + batch_size) / len(review_texts), 1.0)
                progress_bar.progress(progress)

            progress_bar.empty()
            st.success("Sentiment analysis completed!")

            return results

    def get_analyzed_data(self, confidence_threshold, chunk_size):
        """Get or create analyzed data with caching"""
        # Create cache key based on parameters
        cache_key = f"{confidence_threshold}_{chunk_size}"

        if (
            self.analyzed_df is not None
            and hasattr(self, "_cache_key")
            and self._cache_key == cache_key
        ):
            return self.analyzed_df

        if self.df is None:
            return None

        # Initialize sentiment analyzer with parameters
        self.sentiment_analyzer = SentimentAnalyzer(confidence_threshold, chunk_size)

        # Perform sentiment analysis with caching
        review_texts = self.df["review_text"].tolist()
        results = self.perform_sentiment_analysis(
            review_texts, confidence_threshold, chunk_size
        )

        # Create analyzed dataframe
        self.analyzed_df = self.df.copy()
        sentiment_df = pd.DataFrame(results)
        self.analyzed_df["sentiment"] = sentiment_df["sentiment"]
        self.analyzed_df["sentiment_confidence"] = sentiment_df["confidence"]

        # Store cache key
        self._cache_key = cache_key

        return self.analyzed_df

    def create_visualizations(self, confidence_threshold, chunk_size):
        """Create all visualizations"""
        analyzed_df = self.get_analyzed_data(confidence_threshold, chunk_size)
        if analyzed_df is None:
            return

        # Update self.df to use analyzed data for visualizations
        self.df = analyzed_df

        # Create tabs for different visualizations
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "📊 Overview",
                "📈 Trends",
                "⭐ Ratings Analysis",
                "☁️ Word Clouds",
                "📋 Detailed View",
            ]
        )

        with tab1:
            self.overview_tab(confidence_threshold, chunk_size)

        with tab2:
            self.trends_tab()

        with tab3:
            self.ratings_tab()

        with tab4:
            self.wordcloud_tab()

        with tab5:
            self.detailed_tab()

    def overview_tab(self, confidence_threshold, chunk_size):
        """Create overview visualizations"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Reviews", len(self.df))

        with col2:
            avg_confidence = self.df["sentiment_confidence"].mean()
            st.metric("Avg Confidence", f"{avg_confidence:.3f}")

        with col3:
            unique_books = self.df["book_title"].nunique()
            st.metric("Unique Books", unique_books)

        with col4:
            # Add model info with parameters
            st.metric("Model", "BERT Multi")

        # Show current parameters
        st.info(
            f"📊 **Analysis Settings:** Confidence Threshold: {confidence_threshold:.2f} | Chunk Size: {chunk_size} words"
        )

        # Sentiment distribution
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Sentiment Distribution")
            sentiment_counts = self.df["sentiment"].value_counts()

            fig = px.pie(
                values=sentiment_counts.values,
                names=sentiment_counts.index,
                title="Review Sentiment Distribution",
                color_discrete_map={
                    "positive": "#2E8B57",
                    "neutral": "#DAA520",
                    "negative": "#DC143C",
                },
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("📊 Rating Distribution")
            rating_counts = self.df["rating"].value_counts().sort_index()

            fig = px.bar(
                x=rating_counts.index,
                y=rating_counts.values,
                title="Rating Distribution",
                labels={"x": "Rating", "y": "Count"},
                color=rating_counts.values,
                color_continuous_scale="viridis",
            )
            st.plotly_chart(fig, use_container_width=True)

    def trends_tab(self):
        """Create trend analysis visualizations"""
        st.subheader("📈 Sentiment Trends Over Time")

        # Group by month
        self.df["month"] = self.df["date"].dt.to_period("M")
        monthly_sentiment = (
            self.df.groupby(["month", "sentiment"]).size().unstack(fill_value=0)
        )
        monthly_sentiment.index = monthly_sentiment.index.to_timestamp()

        fig = px.line(
            monthly_sentiment,
            title="Sentiment Trends Over Time",
            labels={"value": "Number of Reviews", "index": "Month"},
            color_discrete_map={
                "positive": "#2E8B57",
                "neutral": "#DAA520",
                "negative": "#DC143C",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

        # Average rating over time
        st.subheader("⭐ Average Rating Trends")
        monthly_rating = self.df.groupby("month")["rating"].mean()
        monthly_rating.index = monthly_rating.index.to_timestamp()

        fig = px.line(
            x=monthly_rating.index,
            y=monthly_rating.values,
            title="Average Rating Over Time",
            labels={"x": "Month", "y": "Average Rating"},
        )
        fig.add_hline(
            y=monthly_rating.mean(),
            line_dash="dash",
            annotation_text=f"Overall Average: {monthly_rating.mean():.2f}",
        )
        st.plotly_chart(fig, use_container_width=True)

    def ratings_tab(self):
        """Create rating analysis visualizations"""
        st.subheader("⭐ Rating vs Sentiment Analysis")

        # Correlation heatmap
        col1, col2 = st.columns(2)

        with col1:
            # Rating vs Sentiment crosstab
            crosstab = pd.crosstab(self.df["rating"], self.df["sentiment"])

            fig = px.imshow(
                crosstab.values,
                x=crosstab.columns,
                y=crosstab.index,
                title="Rating vs Sentiment Heatmap",
                color_continuous_scale="RdYlGn",
                text_auto=True,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Sentiment confidence by rating
            confidence_by_rating = (
                self.df.groupby(["rating", "sentiment"])["sentiment_confidence"]
                .mean()
                .unstack()
            )

            fig = px.bar(
                confidence_by_rating,
                title="Average Sentiment Confidence by Rating",
                labels={"value": "Confidence Score", "index": "Rating"},
                color_discrete_map={
                    "positive": "#2E8B57",
                    "neutral": "#DAA520",
                    "negative": "#DC143C",
                },
            )
            st.plotly_chart(fig, use_container_width=True)

        # Review length analysis
        st.subheader("📏 Review Length Analysis")

        fig = px.box(
            self.df,
            x="sentiment",
            y="review_length",
            title="Review Length Distribution by Sentiment",
            color="sentiment",
            color_discrete_map={
                "positive": "#2E8B57",
                "neutral": "#DAA520",
                "negative": "#DC143C",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    def wordcloud_tab(self):
        """Create word cloud visualizations"""
        st.subheader("☁️ Word Clouds by Sentiment")

        col1, col2, col3 = st.columns(3)

        sentiments = ["positive", "negative", "neutral"]
        colors = ["#2E8B57", "#DC143C", "#DAA520"]

        for col, sentiment, color in zip([col1, col2, col3], sentiments, colors):
            with col:
                st.write(f"**{sentiment.title()} Reviews**")

                # Get text for this sentiment
                sentiment_text = " ".join(
                    self.df[self.df["sentiment"] == sentiment]["cleaned_text"].astype(
                        str
                    )
                )

                if sentiment_text.strip():
                    wordcloud = WordCloud(
                        width=300,
                        height=200,
                        background_color="white",
                        colormap="viridis"
                        if sentiment == "positive"
                        else "Reds"
                        if sentiment == "negative"
                        else "Oranges",
                        max_words=50,
                    ).generate(sentiment_text)

                    fig, ax = plt.subplots(figsize=(6, 4))
                    ax.imshow(wordcloud, interpolation="bilinear")
                    ax.axis("off")
                    st.pyplot(fig)
                    plt.close()
                else:
                    st.write("No data available for word cloud")

        # Most common words comparison
        st.subheader("🔤 Most Common Words by Sentiment")

        pos_words = " ".join(
            self.df[self.df["sentiment"] == "positive"]["cleaned_text"].astype(str)
        ).split()
        neg_words = " ".join(
            self.df[self.df["sentiment"] == "negative"]["cleaned_text"].astype(str)
        ).split()

        if pos_words and neg_words:
            pos_common = Counter(pos_words).most_common(10)
            neg_common = Counter(neg_words).most_common(10)

            col1, col2 = st.columns(2)

            with col1:
                if pos_common:
                    pos_df = pd.DataFrame(pos_common, columns=["Word", "Count"])
                    fig = px.bar(
                        pos_df,
                        x="Count",
                        y="Word",
                        orientation="h",
                        title="Top Words in Positive Reviews",
                        color_discrete_sequence=["#2E8B57"],
                    )
                    fig.update_layout(yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                if neg_common:
                    neg_df = pd.DataFrame(neg_common, columns=["Word", "Count"])
                    fig = px.bar(
                        neg_df,
                        x="Count",
                        y="Word",
                        orientation="h",
                        title="Top Words in Negative Reviews",
                        color_discrete_sequence=["#DC143C"],
                    )
                    fig.update_layout(yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig, use_container_width=True)

    def detailed_tab(self):
        """Create detailed data view"""
        st.subheader("📋 Detailed Review Analysis")

        # Filters
        col1, col2, col3 = st.columns(3)

        with col1:
            sentiment_filter = st.multiselect(
                "Filter by Sentiment:",
                options=self.df["sentiment"].unique(),
                default=self.df["sentiment"].unique(),
            )

        with col2:
            rating_filter = st.multiselect(
                "Filter by Rating:",
                options=sorted(self.df["rating"].unique()),
                default=sorted(self.df["rating"].unique()),
            )

        with col3:
            book_filter = st.multiselect(
                "Filter by Book:",
                options=sorted(self.df["book_title"].unique()),
                default=sorted(self.df["book_title"].unique())[
                    :5
                ],  # Show first 5 by default
            )

        # Apply filters
        filtered_df = self.df[
            (self.df["sentiment"].isin(sentiment_filter))
            & (self.df["rating"].isin(rating_filter))
            & (self.df["book_title"].isin(book_filter))
        ]

        st.write(
            f"Showing {len(filtered_df)} reviews (filtered from {len(self.df)} total)"
        )

        # Display filtered data
        display_columns = [
            "book_title",
            "rating",
            "sentiment",
            "sentiment_confidence",
            "review_text",
            "date",
            "reviewer",
        ]

        st.dataframe(
            filtered_df[display_columns].sort_values("date", ascending=False),
            use_container_width=True,
            height=400,
        )

        # Download filtered data
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name=f"sentiment_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

    def run(self):
        """Main run function"""
        download_nltk_data()

        self.setup_page()

        # Sidebar controls
        confidence_threshold, chunk_size, data_source, sample_size = (
            self.sidebar_controls()
        )

        # Load data
        if not self.load_data(data_source, sample_size):
            return

        # Preprocess data
        self.preprocess_data()

        # Create visualizations (sentiment analysis happens automatically with caching)
        self.create_visualizations(confidence_threshold, chunk_size)

        # Footer
        st.markdown("---")
        st.markdown(
            "Built with ❤️ using Streamlit, Plotly, and BERT multilingual sentiment model. "
            "This dashboard provides comprehensive sentiment analysis of book reviews with fine-tunable parameters."
        )


if __name__ == "__main__":
    dashboard = Dashboard()
    dashboard.run()
